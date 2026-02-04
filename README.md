# Astro

A modular AI agent orchestration framework built to answer a practical question: does structured multi-agent orchestration actually produce better results than simpler approaches?

## Why I Built This

I spent the past year building a production multi-agent research system at Goldman Sachs. That work taught me a lot about what breaks when you scale agent workflows — tool contamination across workers, prompt maintenance nightmares, no visibility into why agents made specific decisions. Astro is my attempt to generalize those lessons into a framework with three core ideas:

- **Stars**: Modular prompt components with metadata, versioning, and directed relationships — replacing monolithic prompt blocks with composable, maintainable units
- **Probes**: Capability-scoped tool access that enforces principle-of-least-privilege per workflow step, preventing cross-contamination between agents
- **Constellations**: Directed workflow graphs that define execution paths, branching conditions, and parallel operations across Stars
- **Sidekick**: An execution observability system that captures structured traces — LLM calls, tool invocations, latency, quality signals — for debugging and performance analysis

## What I Found

After building the framework, I benchmarked it honestly against simpler approaches: orchestrated multi-agent (Astro) vs. naive multi-agent vs. zero-shot, using LLM-as-judge evaluation with multiple runs for statistical validity.

The results were more nuanced than I expected:

- **Tool-level scoping works.** Probes effectively prevent cross-contamination between workflow steps.
- **Analysis-level contamination persists.** Even with scoped tools, contamination leaks through at the synthesis layer when agents share context.
- **Orchestration improves independence, not necessarily quality.** Multi-agent orchestration produces more analytically independent outputs, but doesn't consistently justify its cost premium on output quality alone.
- **The value is in the platform, not the architecture.** The real benefit is maintainability, observability, and team workflow — not raw output superiority.

These aren't the findings I wanted, but they're the findings I trust. I've written about these tradeoffs in more detail on [LinkedIn](https://linkedin.com/in/rishimeka).

## Architecture

```
├── astro/                      # Core orchestration framework
│   ├── astro_backend_service/  # Python backend (FastAPI)
│   │   ├── api/                # REST API routes
│   │   ├── foundry/            # MongoDB persistence layer
│   │   ├── models/             # Pydantic models
│   │   ├── probes/             # Tool definitions
│   │   ├── executor/           # Constellation runner
│   │   └── launchpad/          # Chat interface & triggering agent
│   ├── astro-ui/               # Next.js frontend
│   ├── scripts/                # Utility scripts
│   └── requirements.txt        # Python dependencies
├── astrix-labs-uitk/           # Shared UI component library
```
