"use client"

import React from 'react';
import Text, { Typography } from "../foundationalComponents/Text";

export default function WhoThisIsFor() {
    return (
        <section className="who-this-is-for-section" aria-label="Who this is for">
            <div className="who-this-is-for-inner">
                <Text typography={Typography.HEADING_02} className="m-0 color-accent">
                    Who This Is For
                </Text>
                
                <Text typography={Typography.BODY_01} className="mt-4">
                    Astrix is built for <span className="code-style">platform</span> and <span className="code-style">infrastructure</span> teams deploying AI into production environments where failure is expensive.
                    If you are responsible for reliability, observability, or correctness across autonomous systems, this is for you.
                </Text>
                
                <Text typography={Typography.BODY_01} className="mt-3" style={{ opacity: 0.9 }}>
                    This is not a demo framework. It is infrastructure.
                </Text>
            </div>
        </section>
    );
}
