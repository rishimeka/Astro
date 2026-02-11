"""Launchpad: Conversational interface layer for Astro.

The launchpad provides a conversational interface that routes between
two execution modes:

1. Zero-shot (default): Fast execution with directive selection
2. Constellation (research): Thorough multi-agent workflows

## Main Components

- **LaunchpadController**: Routes between execution modes
- **ZeroShotPipeline**: Fast 4-step pipeline (interpret → retrieve → execute → persist)
- **ConstellationPipeline**: Thorough 4-step pipeline (match → retrieve → execute → persist)
- **Interpreter**: Selects relevant directives for queries
- **RunningAgent**: Executes with ReAct loop and scoped tools

## Usage

```python
from astro.launchpad import LaunchpadController
from astro.launchpad.conversation import Conversation

# Create controller (see API dependencies for wiring)
controller = LaunchpadController(zero_shot_pipeline, constellation_pipeline)

# Create conversation
conversation = Conversation()

# Handle message (default: zero-shot mode)
response = await controller.handle_message("What is Tesla's stock price?", conversation)

# Handle message (research mode)
response = await controller.handle_message(
    "Analyze Tesla's financial performance",
    conversation,
    research_mode=True,
)
```
"""

from astro.launchpad.controller import LaunchpadController, Response
from astro.launchpad.conversation import Conversation, Message, PendingConstellation
from astro.launchpad.interpreter import (
    DirectiveSummary,
    InterpretationResult,
    Interpreter,
)
from astro.launchpad.matching import ConstellationMatch, find_matching_constellation
from astro.launchpad.pipelines.constellation import (
    ConstellationPipeline,
    ConstellationPipelineOutput,
)
from astro.launchpad.pipelines.zero_shot import ZeroShotPipeline
from astro.launchpad.preferences import UserSynthesisPreferences
from astro.launchpad.running_agent import AgentOutput, RunningAgent
from astro.launchpad.synthesis import SynthesisAgent

__all__ = [
    # Controller
    "LaunchpadController",
    "Response",
    # Conversation
    "Conversation",
    "Message",
    "PendingConstellation",
    # Pipelines
    "ZeroShotPipeline",
    "ConstellationPipeline",
    "ConstellationPipelineOutput",
    # Zero-shot components
    "Interpreter",
    "DirectiveSummary",
    "InterpretationResult",
    "RunningAgent",
    "AgentOutput",
    # Constellation components
    "ConstellationMatch",
    "find_matching_constellation",
    # Synthesis
    "SynthesisAgent",
    "UserSynthesisPreferences",
]
