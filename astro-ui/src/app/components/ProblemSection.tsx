"use client"

import React from 'react';
import WarningCard from "./WarningCard";
import Text, { Typography } from "../foundationalComponents/Text";
import FailureScenario from './FailureScenario';

type Card = {
    header: string;
    bodyLines: string[];
    footer: string;
    statusLabel?: string;
};

export default function ProblemSection() {
    const cards: Card[] = [
        {
            header: 'CONTEXT COLLAPSE DETECTED',
            bodyLines: [
                'Execution state exceeds retained context window',
                'Implicit assumptions discarded without signal',
                'Recovery requires manual rehydration',
            ],
            footer: 'IMPACT: NON-REPRODUCIBLE SYSTEM BEHAVIOR',
            statusLabel: 'STATUS: DEGRADED',
        },
        {
            header: 'SILENT ERROR ACCUMULATION',
            bodyLines: [
                'Outputs remain plausible while correctness degrades',
                'Errors compound across chained executions',
                'Failure detected only after propagation',
            ],
            footer: 'IMPACT: DELAYED AND EXPENSIVE INCIDENTS',
            statusLabel: 'STATUS: WARNING',
        },
        {
            header: 'CONTROL PLANE ABSENT',
            bodyLines: [
                'Execution paths are not observable',
                'No deterministic constraints on behavior',
                'Debugging occurs post-failure',
            ],
            footer: 'IMPACT: SYSTEMIC RELIABILITY FAILURE',
            statusLabel: 'STATUS: CRITICAL',
        },
    ];

    return (
        <section className="problem-section" aria-label="Problem panels">
            <Text typography={Typography.HEADING_02} className="problem-section-title" style={{ color: '#5A4CFF' }}>
                Systemic Failure Modes
            </Text>
            <Text typography={Typography.TITLE_03} className="mt-2">
                Modern AI systems degrade predictably when execution is unconstrained.
            </Text>
            <Text typography={Typography.BODY_02} className="mt-2">
                Without architectural constraints, intelligent systems fail in consistent and observable ways.
            </Text>
            <FailureScenario />
            <div className="problem-row display-flex justify-space-between mt-8">
                {cards.map((c, idx) => (
                    <div className="problem-card" key={idx} role="article" aria-label={`Panel ${idx + 1}`}>
                        <WarningCard
                            ariaLabel={c.header}
                            idLabel={`PANEL_${String(idx + 1).padStart(2, '0')}`}
                            statusLabel={c.statusLabel}
                            title={c.header}
                            messageItems={c.bodyLines}
                            footer={c.footer}
                        />
                    </div>
                ))}
            </div>
        </section>
    );
}
