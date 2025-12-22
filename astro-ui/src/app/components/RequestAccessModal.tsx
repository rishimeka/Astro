"use client";

import React from "react";
import Modal from "../foundationalComponents/Modal";
import Text, { Typography } from "../foundationalComponents/Text";
import FieldWrapper from "../foundationalComponents/FieldWrapper";
import Input from "../foundationalComponents/Input";
import Textarea from "../foundationalComponents/Textarea";
import Button, { ButtonAppearance, ButtonEmphasis } from "../foundationalComponents/Button";
import { useRequestAccess } from "./RequestAccessContext";

export default function RequestAccessModal() {
    const { isOpen, close, initialEmail } = useRequestAccess();

    const [formData, setFormData] = React.useState({
        name: "",
        email: initialEmail || "",
        organization: "",
        message: "",
    });

    React.useEffect(() => {
        setFormData((prev) => ({ ...prev, email: initialEmail || "" }));
    }, [initialEmail]);

    const handleFormSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const form = e.target as HTMLFormElement;

        fetch("/", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams(new FormData(form) as any).toString(),
        })
            .then(() => {
                close();
                setFormData({ name: "", email: "", organization: "", message: "" });
                alert("Request submitted successfully!");
            })
            .catch(() => {
                alert("Error submitting request. Please try again.");
            });
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={close}
            header={
                <div>
                    <Text typography={Typography.HEADING_03}>Request Early Access</Text>
                    <Text typography={Typography.BODY_02} className="mt-2">
                        We're excited to learn more about your use case. Please fill out the form below to request early access.
                    </Text>
                </div>
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

                <div style={{ marginTop: "1.5rem", display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
                    <Button type="button" appearance={ButtonAppearance.BLACK_AND_WHITE} emphasis={ButtonEmphasis.OUTLINE} onClick={close}>
                        Cancel
                    </Button>
                    <Button type="submit" appearance={ButtonAppearance.PRIMARY} emphasis={ButtonEmphasis.HIGHLIGHT}>
                        Submit Request
                    </Button>
                </div>
            </form>
        </Modal>
    );
}
