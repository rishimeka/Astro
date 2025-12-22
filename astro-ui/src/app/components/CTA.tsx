"use client";

import React from "react";
import Text, { Typography } from "../foundationalComponents/Text";
import Button, { ButtonAppearance, ButtonEmphasis } from "../foundationalComponents/Button";
import InputWithButton from "../foundationalComponents/InputWithButton";
import Modal from "../foundationalComponents/Modal";
import Input from "../foundationalComponents/Input";
import Textarea from "../foundationalComponents/Textarea";
import FieldWrapper from "../foundationalComponents/FieldWrapper";
import "../styles/cta.scss";

export default function CTA() {
    const [email, setEmail] = React.useState("");
    const [isModalOpen, setIsModalOpen] = React.useState(false);
    const [formData, setFormData] = React.useState({
        name: "",
        email: "",
        organization: "",
        message: ""
    });

    const handleRequestAccess = () => {
        if (email) {
            setFormData(prev => ({ ...prev, email }));
            setIsModalOpen(true);
        }
    };

    const handleFormSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const form = e.target as HTMLFormElement;
        
        // Submit to Netlify
        fetch("/", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams(new FormData(form) as any).toString()
        })
            .then(() => {
                setIsModalOpen(false);
                setEmail("");
                setFormData({ name: "", email: "", organization: "", message: "" });
                alert("Request submitted successfully!");
            })
            .catch((error) => {
                alert("Error submitting request. Please try again.");
            });
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

            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                header={
                    <Text typography={Typography.TITLE_03}>
                        Request Early Access
                    </Text>
                }
            >
                <form name="request-access" method="POST" data-netlify="true" onSubmit={handleFormSubmit}>
                    <input type="hidden" name="form-name" value="request-access" />
                    
                    <FieldWrapper label="Name" required>
                        <Input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            placeholder="Your name"
                            required
                        />
                    </FieldWrapper>

                    <FieldWrapper label="Email" required className="mt-4">
                        <Input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            placeholder="your.email@company.com"
                            required
                        />
                    </FieldWrapper>

                    <FieldWrapper label="Organization" required className="mt-4">
                        <Input
                            type="text"
                            name="organization"
                            value={formData.organization}
                            onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                            placeholder="Your organization"
                            required
                        />
                    </FieldWrapper>

                    <FieldWrapper label="Message" className="mt-4">
                        <Textarea
                            name="message"
                            value={formData.message}
                            onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                            placeholder="Tell us about your use case..."
                            rows={4}
                        />
                    </FieldWrapper>

                    <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                        <Button
                            type="button"
                            appearance={ButtonAppearance.BLACK_AND_WHITE}
                            emphasis={ButtonEmphasis.OUTLINE}
                            onClick={() => setIsModalOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            appearance={ButtonAppearance.PRIMARY}
                            emphasis={ButtonEmphasis.HIGHLIGHT}
                        >
                            Submit Request
                        </Button>
                    </div>
                </form>
            </Modal>
        </section>
    );
}
