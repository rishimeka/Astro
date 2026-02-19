"""Conversation models for multi-turn chat interactions."""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def generate_id() -> str:
    """Generate a unique ID."""
    return uuid.uuid4().hex[:12]


class Message(BaseModel):
    """A single message in a conversation."""

    id: str = Field(default_factory=generate_id)
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Who sent this message"
    )
    content: str = Field(..., description="The message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # If this message triggered execution
    run_id: str | None = Field(
        default=None, description="Run ID if this message triggered execution"
    )
    constellation_id: str | None = Field(
        default=None, description="Constellation ID if execution was triggered"
    )


class PendingConstellation(BaseModel):
    """Tracks a constellation that is waiting for variables."""

    constellation_id: str = Field(..., description="The constellation to invoke")
    constellation_name: str = Field(
        ..., description="Display name for the constellation"
    )
    collected_variables: dict[str, Any] = Field(
        default_factory=dict, description="Variables collected so far"
    )
    missing_variables: list[str] = Field(
        default_factory=list, description="Variable names still needed"
    )
    variable_descriptions: dict[str, str] = Field(
        default_factory=dict, description="Variable name to description mapping"
    )


class ClarificationState(BaseModel):
    """Tracks a clarification session during interpreter evaluation."""

    rounds_completed: int = Field(default=0, description="Number of Q&A rounds so far")
    max_rounds: int = Field(default=3, description="Maximum allowed rounds")
    original_query: str = Field(
        ..., description="The original ambiguous query that started clarification"
    )
    interpretation_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="History of InterpretationResult dicts from each round",
    )


class Conversation(BaseModel):
    """A multi-turn conversation with message history."""

    id: str = Field(default_factory=generate_id)
    user_id: str | None = Field(default=None, description="For future auth")
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Track what was invoked
    runs: list[str] = Field(
        default_factory=list, description="Run IDs from constellation executions"
    )

    # Track pending constellation awaiting variables
    pending_constellation: PendingConstellation | None = Field(
        default=None, description="Constellation waiting for variable input"
    )

    # Track clarification session for interpreter
    clarification_state: ClarificationState | None = Field(
        default=None, description="Clarification session state during interpretation"
    )

    def add_message(
        self,
        role: Literal["user", "assistant", "system"],
        content: str,
        run_id: str | None = None,
        constellation_id: str | None = None,
    ) -> Message:
        """Add a message to the conversation.

        Args:
            role: Who sent the message.
            content: The message content.
            run_id: Optional run ID if execution was triggered.
            constellation_id: Optional constellation ID.

        Returns:
            The created Message.
        """
        message = Message(
            role=role,
            content=content,
            run_id=run_id,
            constellation_id=constellation_id,
        )
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)

        if run_id and run_id not in self.runs:
            self.runs.append(run_id)

        return message

    def get_context_messages(self, limit: int = 10) -> list[Message]:
        """Get recent messages for context.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            List of recent messages.
        """
        return self.messages[-limit:]

    def to_llm_messages(self, limit: int = 10) -> list[dict[str, str]]:
        """Convert recent messages to LLM format.

        Args:
            limit: Maximum number of messages to include.

        Returns:
            List of dicts with 'role' and 'content'.
        """
        messages = self.get_context_messages(limit)
        return [{"role": m.role, "content": m.content} for m in messages]

    def set_pending_constellation(
        self,
        constellation_id: str,
        constellation_name: str,
        collected_variables: dict[str, Any],
        missing_variables: list[str],
        variable_descriptions: dict[str, str],
    ) -> None:
        """Set a pending constellation that needs variable collection.

        Args:
            constellation_id: The constellation to invoke once complete.
            constellation_name: Display name for user messages.
            collected_variables: Variables already collected.
            missing_variables: Variable names still needed.
            variable_descriptions: Mapping of variable names to descriptions.
        """
        self.pending_constellation = PendingConstellation(
            constellation_id=constellation_id,
            constellation_name=constellation_name,
            collected_variables=collected_variables,
            missing_variables=missing_variables,
            variable_descriptions=variable_descriptions,
        )
        self.updated_at = datetime.now(UTC)

    def add_collected_variable(self, name: str, value: Any) -> None:
        """Add a collected variable value to the pending constellation.

        Args:
            name: The variable name.
            value: The collected value.
        """
        if self.pending_constellation:
            self.pending_constellation.collected_variables[name] = value
            if name in self.pending_constellation.missing_variables:
                self.pending_constellation.missing_variables.remove(name)
            self.updated_at = datetime.now(UTC)

    def clear_pending_constellation(self) -> None:
        """Clear the pending constellation state."""
        self.pending_constellation = None
        self.updated_at = datetime.now(UTC)

    def has_pending_constellation(self) -> bool:
        """Check if there's a pending constellation awaiting variables."""
        return self.pending_constellation is not None

    def is_pending_complete(self) -> bool:
        """Check if all pending constellation variables have been collected."""
        if not self.pending_constellation:
            return False
        return len(self.pending_constellation.missing_variables) == 0

    def start_clarification(self, original_query: str, max_rounds: int = 3) -> None:
        """Start a new clarification session.

        Args:
            original_query: The ambiguous query that triggered clarification.
            max_rounds: Maximum number of clarification rounds (default 3).
        """
        self.clarification_state = ClarificationState(
            rounds_completed=0,
            max_rounds=max_rounds,
            original_query=original_query,
            interpretation_history=[],
        )
        self.updated_at = datetime.now(UTC)

    def increment_clarification_round(self, interpretation_dict: dict[str, Any]) -> None:
        """Increment the clarification round and store interpretation result.

        Args:
            interpretation_dict: InterpretationResult dict from this round.
        """
        if self.clarification_state:
            self.clarification_state.rounds_completed += 1
            self.clarification_state.interpretation_history.append(interpretation_dict)
            self.updated_at = datetime.now(UTC)

    def should_force_decision(self) -> bool:
        """Check if we've reached max rounds and must force a decision.

        Returns:
            True if max rounds reached, False otherwise.
        """
        if not self.clarification_state:
            return False
        return (
            self.clarification_state.rounds_completed
            >= self.clarification_state.max_rounds
        )

    def clear_clarification(self) -> None:
        """Clear the clarification state."""
        self.clarification_state = None
        self.updated_at = datetime.now(UTC)

    def is_in_clarification(self) -> bool:
        """Check if currently in a clarification session.

        Returns:
            True if clarification state exists, False otherwise.
        """
        return self.clarification_state is not None
