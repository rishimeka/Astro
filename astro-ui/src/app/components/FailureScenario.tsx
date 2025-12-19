"use client"

import React from 'react';
import Text, { Typography } from "../foundationalComponents/Text";

export default function FailureScenario() {
    return (
        <section className="failure-scenario" aria-label="Pattern Recognition">
            <div className="failure-scenario-inner">
                <Text typography={Typography.HEADING_04} className="failure-scenario-label color-accent">
                    A pattern teams recognize too late
                </Text>
                
                <Text typography={Typography.BODY_01} className="failure-scenario-lead mt-3">
                    An agent passes evaluation on Friday.
                    On Monday, the same workflow silently breaks.
                    Nothing changed except the context that came before it.
                </Text>

                <ul className="failure-scenario-list mt-4">
                    <li>
                        <Text typography={Typography.BODY_01}>
                            A tool call fails once, corrupts state, and the error surfaces downstream.
                        </Text>
                    </li>
                    <li>
                        <Text typography={Typography.BODY_01}>
                            Outputs remain plausible while correctness degrades.
                        </Text>
                    </li>
                    <li>
                        <Text typography={Typography.BODY_01}>
                            Debugging starts after impact, not before.
                        </Text>
                    </li>
                </ul>
            </div>
        </section>
    );
}
