"use client"

import React from 'react';
import Text, { Typography } from "../foundationalComponents/Text";

export default function WhyItMatters() {
    return (
        <section className="why-it-matters-section" aria-label="Why it matters">
            <div className="why-it-matters-inner">
                <Text typography={Typography.HEADING_02} className="m-0 color-accent">
                    Why It Matters
                </Text>

                <Text typography={Typography.TITLE_02} className="mt-4">
                    Experiments → Infrastructure.
                </Text>

                <Text typography={Typography.BODY_01} className="mt-4">
                    The gap between “it works in the demo” and “it runs in production” is architectural.
                    Intelligence without structure is inherently unstable.
                    Structure without intelligence is rigid. Astrix bridges that gap.
                </Text>

                <Text typography={Typography.BODY_01} className="mt-3">
                    Systems that matter require guarantees.
                    Guarantees require architecture.
                    This is the infrastructure layer that makes autonomous intelligence deployable in the real world, governable at scale, and trustworthy over time.
                </Text>
            </div>
        </section>
    );
}
