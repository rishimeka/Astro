"""Constellation matching logic for the triggering agent."""

from typing import Any, Dict, List, Optional

from astro_backend_service.launchpad.conversation import Message


class ConstellationMatch:
    """Result of constellation matching."""

    def __init__(
        self,
        constellation_id: str,
        extracted_variables: Dict[str, Any],
        missing_variables: List[str],
        confidence: float = 1.0,
    ) -> None:
        self.constellation_id = constellation_id
        self.extracted_variables = extracted_variables
        self.missing_variables = missing_variables
        self.confidence = confidence

    def is_complete(self) -> bool:
        """Check if all required variables are present."""
        return len(self.missing_variables) == 0


def find_matching_constellation(
    query: str,
    conversation_history: List[Message],
    constellation_summaries: List[Dict[str, Any]],
    llm_client: Any = None,
) -> Optional[ConstellationMatch]:
    """Find constellation matching the query.

    Uses LLM to:
    1. Match query intent to constellation descriptions
    2. Extract variable values from query + conversation
    3. Identify missing required variables

    Args:
        query: The user's query.
        conversation_history: Previous messages for context.
        constellation_summaries: List of constellation summaries from Foundry.
        llm_client: Optional LLM client for matching (stub if None).

    Returns:
        ConstellationMatch with (id, extracted_variables, missing_variables)
        or None if no match.
    """
    if not constellation_summaries:
        return None

    # Build context from conversation
    context = _build_conversation_context(conversation_history)

    # Try LLM-based matching first if client is available
    if llm_client is not None:
        match = _llm_match_constellation(
            query, context, constellation_summaries, llm_client
        )
        if match:
            return match

    # Fallback to keyword matching
    for summary in constellation_summaries:
        description_lower = summary.get("description", "").lower()
        name_lower = summary.get("name", "").lower()
        query_lower = query.lower()

        if _has_keyword_match(query_lower, description_lower, name_lower):
            extracted = extract_variables_from_conversation(
                query,
                conversation_history,
                summary.get("required_variables", []),
                llm_client,
            )

            missing = []
            for var_info in summary.get("required_variables", []):
                if var_info.get("required", False):
                    if var_info["name"] not in extracted:
                        missing.append(var_info["name"])

            return ConstellationMatch(
                constellation_id=summary["id"],
                extracted_variables=extracted,
                missing_variables=missing,
                confidence=0.8,
            )

    return None


def _llm_match_constellation(
    query: str,
    context: str,
    summaries: List[Dict[str, Any]],
    llm_client: Any,
) -> Optional[ConstellationMatch]:
    """Use LLM to match query to best constellation.

    Args:
        query: The user's query.
        context: Conversation context string.
        summaries: Available constellation summaries.
        llm_client: The LLM client.

    Returns:
        ConstellationMatch or None.
    """
    import json
    from langchain_core.messages import HumanMessage, SystemMessage

    # Build constellation list for the prompt
    constellation_list = []
    for i, s in enumerate(summaries):
        vars_desc = ", ".join(
            f"{v['name']} ({v.get('description', 'no description')})"
            for v in s.get("required_variables", [])
        )
        constellation_list.append(
            f"{i+1}. ID: {s['id']}\n"
            f"   Name: {s.get('name', 'Unnamed')}\n"
            f"   Description: {s.get('description', 'No description')}\n"
            f"   Variables: {vars_desc or 'None'}"
        )

    constellations_text = "\n\n".join(constellation_list)

    system_prompt = """You are a constellation matcher. Given a user query and available constellations, determine if any constellation matches the user's intent.

Respond with JSON in this exact format:
{"match": true, "constellation_id": "the-id", "extracted_variables": {"var_name": "value"}, "confidence": 0.9}

Or if no match:
{"match": false}

Only match if the constellation is genuinely relevant to what the user is asking. Extract any variable values mentioned in the query."""

    user_prompt = f"""User query: {query}

Conversation context:
{context or "(New conversation)"}

Available constellations:
{constellations_text}

Which constellation (if any) matches this query? Extract any variable values from the query."""

    try:
        response = llm_client.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        # Parse the response
        content = response.content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)

        if result.get("match") and result.get("constellation_id"):
            constellation_id = result["constellation_id"]
            extracted = result.get("extracted_variables", {})

            # Find the matching summary to get variable specs
            matching_summary = None
            for s in summaries:
                if s["id"] == constellation_id:
                    matching_summary = s
                    break

            if matching_summary:
                # Find missing required variables
                missing = []
                for var_info in matching_summary.get("required_variables", []):
                    if var_info.get("required", False):
                        if var_info["name"] not in extracted:
                            missing.append(var_info["name"])

                return ConstellationMatch(
                    constellation_id=constellation_id,
                    extracted_variables=extracted,
                    missing_variables=missing,
                    confidence=result.get("confidence", 0.8),
                )

    except Exception:
        # Fall back to keyword matching on any error
        pass

    return None


def _build_conversation_context(messages: List[Message]) -> str:
    """Build context string from conversation history."""
    context_parts = []
    for msg in messages[-5:]:  # Last 5 messages
        if msg.role == "user":
            context_parts.append(f"User: {msg.content}")
        elif msg.role == "assistant":
            context_parts.append(f"Assistant: {msg.content}")
    return "\n".join(context_parts)


def _has_keyword_match(query: str, description: str, name: str) -> bool:
    """Check for keyword overlap between query and constellation info."""
    # Extract significant words (simple approach)
    query_words = set(query.split())
    desc_words = set(description.split())
    name_words = set(name.split())

    # Check for overlap (excluding common words)
    common_words = {"the", "a", "an", "is", "are", "to", "for", "and", "or", "of", "in"}
    query_significant = query_words - common_words
    target_significant = (desc_words | name_words) - common_words

    overlap = query_significant & target_significant
    return len(overlap) >= 1


def extract_variables_from_conversation(
    query: str,
    conversation_history: List[Message],
    variable_specs: List[Dict[str, Any]],
    llm_client: Any = None,
) -> Dict[str, Any]:
    """Extract variable values from query and conversation history.

    Args:
        query: The current user query.
        conversation_history: Previous messages.
        variable_specs: List of variable specifications with name, type, description.
        llm_client: Optional LLM client for extraction.

    Returns:
        Dict of variable name to extracted value.
    """
    if not variable_specs:
        return {}

    extracted: Dict[str, Any] = {}

    # Combine query with recent history for extraction
    all_text = query
    for msg in conversation_history[-5:]:  # Last 5 messages
        if msg.role == "user":
            all_text += " " + msg.content

    # Try LLM-based extraction if client is available
    if llm_client is not None:
        llm_extracted = _llm_extract_variables(all_text, variable_specs, llm_client)
        if llm_extracted:
            return llm_extracted

    # Fallback to heuristic extraction
    for var_spec in variable_specs:
        var_name = var_spec.get("name", "")
        var_type = var_spec.get("type", "string")
        var_desc = var_spec.get("description", "")

        # Try to find value based on type and description
        value = _extract_value_heuristic(all_text, var_name, var_type, var_desc)
        if value is not None:
            extracted[var_name] = value

    return extracted


def _llm_extract_variables(
    text: str,
    variable_specs: List[Dict[str, Any]],
    llm_client: Any,
) -> Dict[str, Any]:
    """Use LLM to extract variable values from text.

    Args:
        text: Combined text from query and conversation.
        variable_specs: List of variable specifications.
        llm_client: The LLM client.

    Returns:
        Dict of variable name to extracted value.
    """
    import json
    from langchain_core.messages import HumanMessage, SystemMessage

    # Build variable list for the prompt
    var_descriptions = []
    for spec in variable_specs:
        name = spec.get("name", "")
        var_type = spec.get("type", "string")
        desc = spec.get("description", "no description")
        required = spec.get("required", False)
        req_str = "(required)" if required else "(optional)"
        var_descriptions.append(f"- {name} ({var_type}) {req_str}: {desc}")

    vars_text = "\n".join(var_descriptions)

    system_prompt = """You are a variable extractor. Given user text and a list of variables to extract, identify any values mentioned in the text that correspond to the variables.

Respond with JSON in this exact format:
{"extracted": {"variable_name": "value", "another_var": "value"}}

Only include variables where you found a clear value in the text. Do not make up values.
For company names, look for proper nouns. For tickers, look for 2-5 character uppercase codes.
If no values can be extracted, return: {"extracted": {}}"""

    user_prompt = f"""Text to analyze:
{text}

Variables to extract:
{vars_text}

Extract any variable values you can find in the text."""

    try:
        response = llm_client.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        content = response.content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        return result.get("extracted", {})

    except Exception:
        # Fall back to heuristic extraction on any error
        return {}


def _extract_value_heuristic(
    text: str, var_name: str, var_type: str, var_desc: str
) -> Optional[Any]:
    """Simple heuristic to extract variable values.

    Fallback when LLM is not available.
    """
    text.lower()

    # Common command/action words that should not be treated as values
    command_words = {
        "the",
        "what",
        "how",
        "why",
        "analyze",
        "compare",
        "run",
        "execute",
        "start",
        "trigger",
        "invoke",
        "launch",
        "please",
        "can",
        "could",
        "would",
        "should",
        "will",
        "research",
        "market",
        "company",
        "workflow",
        "constellation",
        "help",
        "me",
        "with",
        "about",
        "for",
        "and",
        "or",
        "this",
    }

    # Company name extraction (common pattern)
    if "company" in var_name.lower() or "company" in var_desc.lower():
        # Look for capitalized words that might be company names
        # Skip if the text looks like a command rather than containing data
        words = text.split()

        # Try to find actual company names - look for proper nouns
        # that aren't command words
        candidates = []
        for i, word in enumerate(words):
            # Skip words that are in the command list
            if word.lower() in command_words:
                continue

            # Skip if the word is all lowercase
            if not word[0:1].isupper():
                continue

            # Skip very short words (likely not company names)
            if len(word) < 3:
                continue

            # This looks like a potential company name
            candidates.append(word)

        # Return the first candidate if found
        if candidates:
            return candidates[0]

    # Ticker extraction
    if "ticker" in var_name.lower() or "symbol" in var_name.lower():
        # Look for all-caps short words
        words = text.split()
        for word in words:
            if word.isupper() and 2 <= len(word) <= 5:
                return word

    return None


def get_all_constellation_summaries(foundry: Any) -> List[Dict[str, Any]]:
    """Get summaries of all constellations from Foundry.

    Args:
        foundry: The Foundry instance.

    Returns:
        List of constellation summary dicts.
    """
    from astro_backend_service.launchpad.tools import get_constellation_summary

    summaries = []

    # Use Foundry.list_constellations() to get all constellations
    for constellation in foundry.list_constellations():
        # Skip hidden/internal constellations
        if constellation.metadata and constellation.metadata.get("hidden"):
            continue
        summary = get_constellation_summary(constellation.id, foundry)
        if summary:
            summaries.append(summary)

    return summaries
