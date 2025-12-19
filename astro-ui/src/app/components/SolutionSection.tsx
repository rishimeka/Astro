"use client"

import WarningCard from "./WarningCard";
import Text, { Typography } from "../foundationalComponents/Text";

export default function SolutionSection() {
    const solutions = [
        {
            title: "Modular Intelligence, Not Monolithic Prompts",
            leadingClause: "Architecture starts with decomposition.",
            content: "We move beyond the fragility of massive context windows. Astrix treats intelligence as composable modules. This decouples model weights from application logic, allowing you to swap providers, version prompts, and optimize specific cognitive tasks without rewriting your entire stack."
        },
        {
            title: "Deterministic Control Over Execution and Tools",
            leadingClause: "Control requires enforcement, not suggestion.",
            content: "Probabilistic reasoning requires deterministic guardrails. Our runtime enforces strict typing on all inputs and outputs, ensuring that tool execution adheres to defined schemas and that failures are caught at the logic layer, not the user interface."
        },
        {
            title: "Graph-Based Reasoning Instead of Linear Chains",
            leadingClause: "Real systems branch, loop, and adapt.",
            content: "Real-world problem solving isn't linear. Our engine supports complex Directed Acyclic Graphs (DAGs), enabling dynamic branching, recursive loops, and parallel execution paths that adapt based on intermediate state context rather than rigid sequential chains."
        },
        {
            title: "Continuous Self-Improvement with Human Governance",
            leadingClause: "Learning systems still need human veto power.",
            content: "Close the loop between deployment and development. Astrix captures comprehensive execution traces. Engineers can identify stochastic failures, patch logic, and replay historical executions against evolving logic and constraints to verify fixes, creating a system that hardens over time."
        },
        {
            title: "The Result",
            leadingClause: null,
            content: "Software that behaves under uncertainty. By decomposing probabilistic execution into explicit mechanics, Astrix enables teams to deploy autonomous systems into mission-critical production environments with confidence."
        }
    ]
    return (
        <section className="solution-section" aria-label="Solution panels">
            <div className="solution-container">
                <div className="solution-left">
                    <Text typography={Typography.HEADING_02} className="m-0 color-accent">
                        The Solution
                    </Text>
                    <Text typography={Typography.TITLE_02} className="mt-2">
                        What We're Building
                    </Text>

                    <div className="solution-thesis mt-4">
                        <Text typography={Typography.BODY_01} style={{ fontWeight: 600 }}>
                            Astrix turns probabilistic reasoning into an engineered system.
                        </Text>
                        <Text typography={Typography.BODY_01} className="mt-2">
                            By making state, constraints, execution paths, and failure modes explicit, we replace fragile prompt behavior with governed, deterministic execution.
                        </Text>
                    </div>

                    <Text typography={Typography.BODY_01} className="mt-4">
                        Think of Astrix as a control plane that sits between your models, tools, and workflows, introducing architecture where intelligence was previously left unconstrained.
                    </Text>
                    <Text typography={Typography.BODY_01} className="mt-4">
                        Astrix exists because probabilistic intelligence cannot be trusted without structural guarantees. This architecture was born out of watching production agents fail silently under real load.
                    </Text>
                </div>

                <div className="solution-right">
                    <div className="solution-row">
                        {solutions.map((s, i) => (
                            <div className="solution-card" key={i}>
                                <Text typography={Typography.TITLE_04} className="color-accent-light">
                                    {s.title}
                                </Text>
                                {s.leadingClause && (
                                    <Text typography={Typography.BODY_02} className="mt-2 solution-leading-clause">
                                        {s.leadingClause}
                                    </Text>
                                )}
                                <Text typography={Typography.BODY_01} className="mt-3">
                                    {s.content}
                                </Text>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}
