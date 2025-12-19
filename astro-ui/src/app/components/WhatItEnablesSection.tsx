"use client"

import Text, { Typography } from "../foundationalComponents/Text";

export default function WhatItEnablesSection() {
    const items = [
        {
            title: "Predictable behavior from inherently probabilistic systems.",
            content: "Astro allows intelligent systems to operate with consistent, bounded behavior even when underlying models are stochastic. Execution remains observable, reproducible, and constrained by explicit rules rather than emergent chance."
        },
        {
            title: "Safe Autonomy at Scale",
            content: "Deploy autonomous agents that act independently without sacrificing control, auditability, or reliability. Systems remain governable even as autonomy increases."
        },
        {
            title: "Evolvable Intelligence Without Regression",
            content: "Improve reasoning capabilities over time without destabilizing existing behavior. Changes are isolated, testable, and reversible, enabling continuous improvement without hidden failures."
        },
        {
            title: "Operational Visibility by Default",
            content: "Every decision path, tool invocation, and failure state is captured as part of normal execution. Engineers understand why a system behaved a certain way, not just what it produced."
        },
        {
            title: "Production-Grade Reliability",
            content: "Intelligent systems behave like software, not experiments. Failures are detected early, traced precisely, and resolved without cascading downstream impact."
        }
    ];

    return (
        <section className="what-it-enables-section" aria-label="What this enables">
            <div className="what-it-enables-container">
                <div className="what-it-enables-inner">
                    <Text typography={Typography.HEADING_02} className="m-0 color-accent">
                        What This Enables
                    </Text>
                    <Text typography={Typography.TITLE_02} className="mt-2">
                        From Prototype to Infrastructure
                    </Text>

                    <div className="mental-model-bridge mt-6">
                        <div className="mental-model-grid">
                            <div className="mental-model-column">
                                <Text typography={Typography.TITLE_03} className="mental-model-header color-accent">
                                    Without Architecture
                                </Text>
                                <div className="mental-model-items">
                                    <Text typography={Typography.BODY_02}>Prompt → Model → Output → Hope</Text>
                                    <Text typography={Typography.BODY_02}>Implicit context</Text>
                                    <Text typography={Typography.BODY_02}>Errors discovered after impact</Text>
                                    <Text typography={Typography.BODY_02}>Debugging symptoms</Text>
                                </div>
                            </div>
                            
                            <div className="mental-model-divider"></div>
                            
                            <div className="mental-model-column">
                                <Text typography={Typography.TITLE_03} className="mental-model-header color-accent">
                                    With Astrix
                                </Text>
                                <div className="mental-model-items">
                                    <Text typography={Typography.BODY_02}>State → Graph → Constrained Execution → Trace</Text>
                                    <Text typography={Typography.BODY_02}>Explicit state</Text>
                                    <Text typography={Typography.BODY_02}>Errors caught at the logic layer</Text>
                                    <Text typography={Typography.BODY_02}>Inspecting execution paths</Text>
                                </div>
                            </div>
                        </div>
                    </div>

                    <Text typography={Typography.TITLE_03} className="mt-10">
                        Operational Guarantees
                    </Text>

                    <div className="what-it-enables-list mt-6">
                        {items.map((it, i) => (
                            <div className="what-it-enables-item mt-2" key={i}>
                                <Text typography={Typography.TITLE_04} className="m-0 color-accent">
                                    {it.title}
                                </Text>

                                <Text typography={Typography.BODY_01} className="mt-2">
                                    {it.content}
                                </Text>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}
