"""File upload routes for handling Excel and document uploads."""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Configurable upload directory - defaults to ./uploads in the project root
UPLOAD_DIR = Path(os.getenv("ASTRO_UPLOAD_DIR", "./uploads"))

# Allowed file extensions (for fund model POC, primarily Excel)
ALLOWED_EXTENSIONS = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".json": "application/json",
}

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class FileMetadata(BaseModel):
    """Metadata for an uploaded file."""

    id: str = Field(..., description="Unique file identifier")
    original_name: str = Field(..., description="Original filename")
    stored_path: str = Field(..., description="Path where file is stored")
    mime_type: str | None = Field(None, description="MIME type of the file")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UploadResponse(BaseModel):
    """Response for file upload."""

    files: list[FileMetadata]
    message: str


class FileListResponse(BaseModel):
    """Response for listing files."""

    files: list[FileMetadata]
    count: int


def ensure_upload_dir() -> Path:
    """Ensure upload directory exists and return its path."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_file_extension(filename: str) -> str:
    """Validate file extension and return the extension."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed types: {list(ALLOWED_EXTENSIONS.keys())}",
        )
    return ext


def generate_stored_filename(original_name: str, file_id: str) -> str:
    """Generate a unique stored filename that preserves the extension."""
    ext = Path(original_name).suffix.lower()
    return f"{file_id}{ext}"


@router.post("", response_model=UploadResponse)
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    """Upload one or more files.

    Files are stored locally and their paths can be passed to constellation runs.

    Args:
        files: List of files to upload (multipart/form-data)

    Returns:
        UploadResponse with metadata for each uploaded file
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    upload_dir = ensure_upload_dir()
    uploaded: list[FileMetadata] = []

    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")

        # Validate extension
        validate_file_extension(file.filename)

        # Read file content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB",
            )

        # Generate unique ID and stored filename
        file_id = str(uuid.uuid4())
        stored_name = generate_stored_filename(file.filename, file_id)
        stored_path = upload_dir / stored_name

        # Write file
        with open(stored_path, "wb") as f:
            f.write(content)

        logger.info(f"Uploaded file: {file.filename} -> {stored_path}")

        metadata = FileMetadata(
            id=file_id,
            original_name=file.filename,
            stored_path=str(stored_path.absolute()),
            mime_type=file.content_type or ALLOWED_EXTENSIONS.get(Path(file.filename).suffix.lower()),
            size_bytes=len(content),
        )
        uploaded.append(metadata)

    return UploadResponse(
        files=uploaded,
        message=f"Successfully uploaded {len(uploaded)} file(s)",
    )


@router.get("/{file_id}", response_model=FileMetadata)
async def get_file_metadata(file_id: str) -> FileMetadata:
    """Get metadata for an uploaded file by ID.

    Args:
        file_id: The unique file identifier

    Returns:
        FileMetadata for the file
    """
    upload_dir = ensure_upload_dir()

    # Find the file by ID (ID is the filename prefix)
    for path in upload_dir.iterdir():
        if path.stem == file_id:
            stat = path.stat()
            return FileMetadata(
                id=file_id,
                original_name=path.name,  # We don't store original name, use stored name
                stored_path=str(path.absolute()),
                mime_type=ALLOWED_EXTENSIONS.get(path.suffix.lower()),
                size_bytes=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime),
            )

    raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found")


@router.delete("/{file_id}")
async def delete_file(file_id: str) -> dict:
    """Delete an uploaded file by ID.

    Args:
        file_id: The unique file identifier

    Returns:
        Confirmation message
    """
    upload_dir = ensure_upload_dir()

    # Find and delete the file
    for path in upload_dir.iterdir():
        if path.stem == file_id:
            path.unlink()
            logger.info(f"Deleted file: {path}")
            return {"message": f"File '{file_id}' deleted successfully"}

    raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found")


@router.get("", response_model=FileListResponse)
async def list_files() -> FileListResponse:
    """List all uploaded files.

    Returns:
        List of FileMetadata for all uploaded files
    """
    upload_dir = ensure_upload_dir()
    files: list[FileMetadata] = []

    for path in upload_dir.iterdir():
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            stat = path.stat()
            files.append(
                FileMetadata(
                    id=path.stem,
                    original_name=path.name,
                    stored_path=str(path.absolute()),
                    mime_type=ALLOWED_EXTENSIONS.get(path.suffix.lower()),
                    size_bytes=stat.st_size,
                    uploaded_at=datetime.fromtimestamp(stat.st_mtime),
                )
            )

    # Sort by upload time descending (most recent first)
    files.sort(key=lambda f: f.uploaded_at, reverse=True)

    return FileListResponse(files=files, count=len(files))
