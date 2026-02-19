"""Constellations router - CRUD and execution endpoints."""

import asyncio
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from astro_api.dependencies import get_orchestration_storage, get_registry, get_runner

logger = logging.getLogger(__name__)
from astro.core.file_processing import format_file_context_for_llm, process_file
from astro.core.models import TemplateVariable
from astro.core.registry import Registry
from astro.orchestration.models import (
    Constellation,
    Edge,
    EndNode,
    Position,
    StarNode,
    StartNode,
)
from astro.orchestration.runner import ConstellationRunner

from astro_api.schemas import (
    ConstellationCreate,
    ConstellationResponse,
    ConstellationSummary,
    ConstellationUpdate,
    RunRequest,
)

router = APIRouter()


def _build_constellation(request: ConstellationCreate) -> Constellation:
    """Build a Constellation model from create request."""
    # Build start node
    start_data = request.start
    start = StartNode(
        id=start_data.get("id", "start"),
        position=Position(**start_data.get("position", {"x": 0, "y": 0})),
    )

    # Build end node
    end_data = request.end
    end = EndNode(
        id=end_data.get("id", "end"),
        position=Position(**end_data.get("position", {"x": 500, "y": 0})),
    )

    # Build star nodes
    nodes = []
    for node_data in request.nodes:
        node = StarNode(
            id=node_data["id"],
            star_id=node_data["star_id"],
            position=Position(**node_data.get("position", {"x": 0, "y": 0})),
            display_name=node_data.get("display_name"),
            requires_confirmation=node_data.get("requires_confirmation", False),
            confirmation_prompt=node_data.get("confirmation_prompt"),
        )
        nodes.append(node)

    # Build edges
    edges = []
    for edge_data in request.edges:
        edge = Edge(
            id=edge_data["id"],
            source=edge_data["source"],
            target=edge_data["target"],
            condition=edge_data.get("condition"),
        )
        edges.append(edge)

    return Constellation(
        id=request.id,
        name=request.name,
        description=request.description,
        start=start,
        end=end,
        nodes=nodes,
        edges=edges,
        max_loop_iterations=request.max_loop_iterations,
        max_retry_attempts=request.max_retry_attempts,
        retry_delay_base=request.retry_delay_base,
        metadata=request.metadata,
    )


@router.get("", response_model=list[ConstellationSummary])
async def list_constellations(
    storage = Depends(get_orchestration_storage),
) -> list[ConstellationSummary]:
    """List all constellations."""
    logger.debug("Listing all constellations")
    constellations = await storage.list_constellations()
    logger.debug(f"Found {len(constellations)} constellations")
    return [
        ConstellationSummary(
            id=c.id,
            name=c.name,
            description=c.description,
            node_count=len(c.nodes),
            tags=c.metadata.get("tags", []),
        )
        for c in constellations
    ]


@router.get("/{id}", response_model=Constellation)
async def get_constellation(
    id: str,
    storage = Depends(get_orchestration_storage),
) -> Constellation:
    """Get a constellation by ID."""
    logger.debug(f"Getting constellation: {id}")
    constellation = await storage.get_constellation(id)
    if constellation is None:
        logger.debug(f"Constellation not found: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")
    return constellation


@router.get("/{id}/variables", response_model=list[TemplateVariable])
async def get_constellation_variables(
    id: str,
    storage = Depends(get_orchestration_storage),
    registry: Registry = Depends(get_registry),
) -> list[TemplateVariable]:
    """Get required variables for a constellation.

    Computes the set of template variables needed by following the chain:
    Constellation -> Stars -> Directives -> Template Variables
    """
    # Get constellation
    constellation = await storage.get_constellation(id)
    if constellation is None:
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")

    # Collect all unique star IDs from constellation nodes
    star_ids = {node.star_id for node in constellation.nodes}

    # Get all stars and collect directive IDs
    directive_ids = set()
    for star_id in star_ids:
        star = await storage.get_star(star_id)
        if star and star.directive_id:
            directive_ids.add(star.directive_id)

    # Get all directives and collect user-provided template variables only
    variables_dict = {}  # Use dict to deduplicate by name
    for directive_id in directive_ids:
        directive = registry.get_directive(directive_id)
        if directive and directive.template_variables:
            for var in directive.template_variables:
                if var.name not in variables_dict and var.user_provided:
                    variables_dict[var.name] = var

    return list(variables_dict.values())


@router.post(
    "", response_model=ConstellationResponse, status_code=status.HTTP_201_CREATED
)
async def create_constellation(
    request: ConstellationCreate,
    storage = Depends(get_orchestration_storage),
) -> ConstellationResponse:
    """Create a new constellation."""
    logger.info(f"Creating constellation: id={request.id}, name={request.name}")
    constellation = _build_constellation(request)

    try:
        created = await storage.save_constellation(constellation)
        logger.info(f"Constellation created: {created.id}")
        return ConstellationResponse(
            constellation=created.model_dump(),
            warnings=[],  # OrchestrationStorage doesn't return warnings
        )
    except Exception as e:
        logger.warning(f"Error creating constellation {request.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=ConstellationResponse)
async def update_constellation(
    id: str,
    request: ConstellationUpdate,
    storage = Depends(get_orchestration_storage),
) -> ConstellationResponse:
    """Update a constellation."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        logger.debug(f"Update constellation {id}: no fields to update")
        raise HTTPException(status_code=400, detail="No fields to update")

    logger.info(f"Updating constellation: {id}, fields={list(updates.keys())}")

    # Get existing constellation
    existing = await storage.get_constellation(id)
    if not existing:
        logger.debug(f"Constellation not found for update: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")

    # Apply updates
    for key, value in updates.items():
        setattr(existing, key, value)

    try:
        updated = await storage.save_constellation(existing)
        logger.info(f"Constellation updated: {id}")
        return ConstellationResponse(
            constellation=updated.model_dump(),
            warnings=[],
        )
    except Exception as e:
        logger.warning(f"Error updating constellation {id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_constellation(
    id: str,
    storage = Depends(get_orchestration_storage),
) -> None:
    """Delete a constellation."""
    logger.info(f"Deleting constellation: {id}")
    deleted = await storage.delete_constellation(id)
    if not deleted:
        logger.debug(f"Constellation not found for deletion: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")
    logger.info(f"Constellation deleted: {id}")


@router.post("/{id}/run")
async def run_constellation(
    id: str,
    variables: str = Form("{}"),  # JSON string of variables
    file: UploadFile | None = File(None),  # Optional file upload
    storage = Depends(get_orchestration_storage),
    runner: ConstellationRunner = Depends(get_runner),
):
    """Execute a constellation in the background and return run ID immediately.

    This endpoint starts the constellation execution and returns the run ID right away,
    allowing other requests to be processed concurrently. Use GET /runs/{run_id}/stream
    to monitor the execution progress via SSE.

    Accepts optional file upload:
    - Excel files (.xlsx, .xls) are parsed into JSON and added to variables
    - PDF files are made available to the model for native processing
    - Other files are stored with basic metadata
    """
    import json

    from astro.orchestration.runner.runner import generate_run_id

    logger.info(f"Run request for constellation: {id}")

    # Parse variables from form data
    try:
        variables_dict = json.loads(variables)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in variables field")

    # Verify constellation exists
    constellation = await storage.get_constellation(id)
    if constellation is None:
        logger.debug(f"Constellation not found for run: {id}")
        raise HTTPException(status_code=404, detail=f"Constellation '{id}' not found")

    # Process uploaded file if present
    file_context = None
    if file and file.filename:
        logger.info(f"Processing uploaded file: {file.filename}")
        try:
            # Save to temporary file
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Process the file
            processed = process_file(tmp_path, file.filename)

            # Add file data to variables based on type
            if processed.data:
                # Excel files: add parsed JSON to variables
                if processed.file_type.value == "excel":
                    variables_dict["excel_data"] = processed.data
                    variables_dict["excel_file_path"] = tmp_path
                # Text files: add content to variables
                elif processed.file_type.value == "text":
                    variables_dict["file_content"] = processed.data.get("content", "")

            # For all file types, add file path for reference
            variables_dict["uploaded_file_path"] = tmp_path
            variables_dict["uploaded_filename"] = file.filename

            # Format file context for LLM
            file_context = format_file_context_for_llm(processed)
            logger.info(f"File processed: {file.filename} (type: {processed.file_type})")

        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}", exc_info=True)
            raise HTTPException(
                status_code=400, detail=f"Error processing file: {str(e)}"
            )

    # Generate run ID upfront
    run_id = generate_run_id()

    # Start execution in background task - do NOT await
    async def execute_in_background():
        """Execute constellation in the background."""
        try:
            logger.debug(
                f"Starting background execution of constellation: {id}, run_id: {run_id}"
            )

            # Add file context to original_query if present
            original_query = variables_dict.get("_query", "")
            if file_context:
                original_query = f"{file_context}\n\n{original_query}"

            await runner.run(
                constellation_id=id,
                variables=variables_dict,
                original_query=original_query,
                run_id=run_id,
            )
            logger.info(f"Background execution completed: run_id={run_id}")
        except Exception as e:
            logger.error(
                f"Error in background execution for constellation {id}: {e}",
                exc_info=True,
            )

    # Start the task but don't wait for it
    asyncio.create_task(execute_in_background())

    # Return immediately with the run ID
    # The client should use /runs/{run_id}/stream to monitor progress
    return {
        "run_id": run_id,
        "constellation_id": id,
        "constellation_name": constellation.name,
        "status": "started",
        "message": f"Execution started in background. Use GET /runs/{run_id}/stream to monitor progress.",
        "file_uploaded": file is not None and file.filename is not None,
    }
