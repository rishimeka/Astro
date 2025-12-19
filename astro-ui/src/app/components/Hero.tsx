"use client"

import React from 'react';
import Text, { Typography } from "../foundationalComponents/Text";
import WarningCard from "./WarningCard";

export default function Hero() {
    return (
        <div className="hero">
            <div className="grid-background-with-fade" />
            <div className="hero-content display-flex justify-space-between align-center">
                <div style={{ maxWidth: '60%' }}>
                    <Text typography={Typography.DISPLAY_01}>
                        Intelligence{' '}
                        <span style={{ color: '#5A4CFF', fontStyle: 'italic' }}>without
                            architecture</span> is just{' '}
                        beautiful noise.
                    </Text>
                    <Text typography={Typography.SUBTITLE_02} style={{ marginTop: '0.5rem', opacity: 0.8 }}>
                        We are building the infrastructure that keeps AI systems coherent.
                    </Text>
                </div>
                <WarningCard
                    ariaLabel="Log entry 01"
                    idLabel="LOG_ENTRY_01"
                    statusLabel="STATUS: WARNING"
                    title="UNCONSTRAINED EXECUTION DETECTED"
                    messageItems={[
                        'Probabilistic behavior without architectural guarantees'
                    ]}
                    footer="RISK CLASSIFICATION: SYSTEMIC"
                />
            </div>
        </div>
    );
}
