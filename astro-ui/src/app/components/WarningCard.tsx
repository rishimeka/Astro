"use client"

import React from 'react';

type WarningCardProps = {
    ariaLabel?: string;
    idLabel?: string;
    statusLabel?: string;
    title?: string;
    messageItems?: string[];
    footer?: string;
};

export default function WarningCard({
    ariaLabel = 'Log entry 01',
    idLabel = 'LOG_ENTRY_01',
    statusLabel = 'STATUS: WARNING',
    title = 'PROBABILISTIC EXECUTION PATH DETECTED',
    messageItems = [
        'Non-deterministic output',
        'Unbounded error accumulation',
        'Control layer absent',
    ],
    footer = 'RISK CLASSIFICATION: SYSTEMIC',
}: WarningCardProps) {
    return (
        <div className="warning-card-wrapper">
            <div className="warning-card-alt" role="region" aria-label={ariaLabel}>
                <div className="wc-row">
                    <span className="wc-small">{idLabel}</span>
                    <span className="wc-status">{statusLabel}</span>
                </div>

                <h3>{title}</h3>

                <div className="wc-message">
                    <ul>
                        {messageItems.map((m, i) => (
                            <li key={i}>{m}</li>
                        ))}
                    </ul>
                </div>

                <div className="wc-footer">{footer}</div>
            </div>
        </div>
    );
}
