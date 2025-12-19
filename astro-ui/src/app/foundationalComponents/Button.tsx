'use client';

import React from 'react';

export enum ButtonAppearance {
    PRIMARY = 'primary',
    BLACK_AND_WHITE = 'black-and-white',
    SUCCESS = 'success',
    ERROR = 'error',
}

export enum ButtonEmphasis {
    HIGHLIGHT = 'highlight',
    OUTLINE = 'outline',
    SUBTLE = 'subtle',
    MINIMAL = 'minimal',
}

export enum ButtonSize {
    XS = 'xs',
    SM = 'sm',
    MD = 'md',
    LG = 'lg',
    XL = 'xl',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    appearance?: ButtonAppearance;
    emphasis?: ButtonEmphasis;
    size?: ButtonSize;
    children: React.ReactNode;
    disabled?: boolean;
}

export default function Button({
    appearance = ButtonAppearance.PRIMARY,
    emphasis = ButtonEmphasis.HIGHLIGHT,
    size = ButtonSize.MD,
    children,
    disabled = false,
    className = '',
    ...props
}: ButtonProps) {
    return (
        <button
            className={`btn btn-${appearance} btn-${emphasis} btn-${size} ${className}`}
            disabled={disabled}
            {...props}
        >
            {children}
        </button>
    );
}
