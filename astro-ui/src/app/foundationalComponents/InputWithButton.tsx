'use client';

import React from 'react';
import Button, { ButtonAppearance, ButtonEmphasis } from './Button';

interface InputWithButtonProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
    buttonText?: string;
    onButtonClick?: () => void;
    buttonAppearance?: ButtonAppearance;
    buttonEmphasis?: ButtonEmphasis;
    error?: boolean;
    disabled?: boolean;
}

export default function InputWithButton({
    buttonText = 'Submit',
    onButtonClick,
    buttonAppearance = ButtonAppearance.PRIMARY,
    buttonEmphasis = ButtonEmphasis.HIGHLIGHT,
    error = false,
    disabled = false,
    className = '',
    ...props
}: InputWithButtonProps) {
    return (
        <div className={`input-with-button ${error ? 'input-with-button-error' : ''} ${disabled ? 'input-with-button-disabled' : ''}`}>
            <input
                type="email"
                className={`input-with-button-input ${className}`}
                disabled={disabled}
                {...props}
            />
            <Button
                onClick={onButtonClick}
                disabled={disabled}
                appearance={buttonAppearance}
                emphasis={buttonEmphasis}
                className="input-with-button-btn"
            >
                {buttonText}
            </Button>
        </div>
    );
}
