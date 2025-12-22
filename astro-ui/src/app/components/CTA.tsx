"use client";

import React from "react";
import { ButtonAppearance, ButtonEmphasis } from "../foundationalComponents/Button";
import InputWithButton from "../foundationalComponents/InputWithButton";
import Text, { Typography } from "../foundationalComponents/Text";
import "../styles/cta.scss";
import { useRequestAccess } from "./RequestAccessContext";

export default function CTA() {
    const [email, setEmail] = React.useState("");
    const { open } = useRequestAccess();

    const handleRequestAccess = () => {
        if (email) {
            open(email);
        }
    };



    return (
        <section className="cta-section">
            {/* Hidden form for Netlify form detection */}
            <form name="request-access" data-netlify="true" hidden>
                <input type="text" name="name" />
                <input type="email" name="email" />
                <input type="text" name="organization" />
                <textarea name="message"></textarea>
            </form>

            <div className="cta-inner">
                <Text typography={Typography.HEADING_02} className="problem-section-title" style={{ color: '#5A4CFF' }}>
                    Access
                </Text>
                <Text typography={Typography.TITLE_03} className="mt-2">
                    Architecture before capability.
                </Text>
                <Text typography={Typography.BODY_01} className="mt-1" style={{ opacity: 0.9 }}>
                    We are onboarding a small number of teams building AI systems they intend to trust.
                </Text>
                <Text typography={Typography.BODY_03} className="cta-body mt-4">
                    Early access is selective. There are no public demos, no playgrounds, and no shortcuts.
                </Text>

                <div className="cta-actions">
                    <InputWithButton
                        placeholder="Enter work email"
                        buttonText="Request early access"
                        buttonAppearance={ButtonAppearance.PRIMARY}
                        buttonEmphasis={ButtonEmphasis.HIGHLIGHT}
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        onButtonClick={handleRequestAccess}
                    />

                    <Text typography={Typography.CAPTION_01} className="cta-microcopy">
                        If failure is expensive and explainability matters, we should talk.
                    </Text>
                </div>

                <Text typography={Typography.CAPTION_01} className="mt-6 cta-enterprise-signal">
                    Designed for environments where correctness, auditability, and control are non-negotiable.
                </Text>
            </div>

            {/* Request access modal moved to a shared component */}
        </section>
    );
}
