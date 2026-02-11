"""DocExStar - document extraction orchestrator."""

import asyncio
from typing import TYPE_CHECKING, Any

from pydantic import Field

from astro.orchestration.models.star_types import StarType
from astro.orchestration.stars.base import OrchestratorStar

if TYPE_CHECKING:
    from astro.core.models.outputs import DocExResult  # type: ignore[attr-defined]
    from astro.orchestration.context import ConstellationContext


class DocExStar(OrchestratorStar):
    """
    Document extraction — one worker per document.
    Parallel execution.
    """

    type: StarType = Field(default=StarType.DOCEX, frozen=True)

    def validate_star(self) -> list[str]:
        """Validate DocExStar configuration."""
        errors = super().validate_star()
        return errors

    async def execute(self, context: "ConstellationContext") -> "DocExResult":
        """Extract information from documents in parallel.

        Args:
            context: Execution context with documents.

        Returns:
            DocExResult with extractions from each document.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from astro.core.llm.utils import get_llm
        from astro.core.models.outputs import (  # type: ignore[attr-defined]
            DocExResult,
            DocumentExtraction,
        )

        # Get documents from context
        documents = context.get_documents()

        if not documents:
            return DocExResult(documents=[])

        # Get directive for extraction instructions
        directive = context.get_directive(self.directive_id)

        async def extract_from_document(doc: Any) -> DocumentExtraction:
            """Extract information from a single document."""
            # Get document content and ID
            if isinstance(doc, dict):
                doc_id = doc.get("id", str(hash(str(doc)))[:8])
                content = doc.get("content", str(doc))
            elif hasattr(doc, "id") and hasattr(doc, "content"):
                doc_id = doc.id
                content = doc.content
            else:
                doc_id = str(hash(str(doc)))[:8]
                content = str(doc)

            system_prompt = f"""{directive.content}

You are a document extraction agent. Extract relevant information from the document according to the instructions above.
Be thorough but concise. Focus on information relevant to the user's request."""

            user_message = f"""Original request: {context.original_query}

Document to analyze:
{content[:10000]}  # Limit content length

Extract the relevant information from this document."""

            llm = get_llm(temperature=0.2)

            try:
                response = llm.invoke(  # type: ignore[attr-defined]
                    [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_message),
                    ]
                )

                raw_content = (
                    response.content if hasattr(response, "content") else str(response)
                )
                extracted = (
                    raw_content if isinstance(raw_content, str) else str(raw_content)
                )

                return DocumentExtraction(
                    doc_id=doc_id,
                    extracted_content=extracted,
                    metadata={"source": doc_id},
                )

            except Exception as e:
                return DocumentExtraction(
                    doc_id=doc_id,
                    extracted_content=f"Error extracting from document: {str(e)}",
                    metadata={"error": str(e)},
                )

        # Execute extractions in parallel
        results = await asyncio.gather(
            *[extract_from_document(doc) for doc in documents], return_exceptions=True
        )

        extractions: list[DocumentExtraction] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                extractions.append(
                    DocumentExtraction(
                        doc_id=f"doc_{i}",
                        extracted_content=f"Error: {str(result)}",
                        metadata={"error": str(result)},
                    )
                )
            elif isinstance(result, DocumentExtraction):
                extractions.append(result)

        return DocExResult(documents=extractions)
