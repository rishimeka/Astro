'use client';

import React, { ReactNode } from 'react';

export enum Typography {
    // Display - Libre Baskerville
    DISPLAY_01 = 'display-01',
    DISPLAY_02 = 'display-02',
    DISPLAY_03 = 'display-03',

    // Titles - Libre Baskerville
    TITLE_01 = 'title-01',
    TITLE_02 = 'title-02',
    TITLE_03 = 'title-03',
    TITLE_04 = 'title-04',

    // Sub-Titles - Outfit
    SUBTITLE_01 = 'subtitle-01',
    SUBTITLE_02 = 'subtitle-02',

    // Headings - Outfit
    HEADING_01 = 'heading-01',
    HEADING_02 = 'heading-02',
    HEADING_03 = 'heading-03',
    HEADING_04 = 'heading-04',

    // Body - JetBrains Mono
    BODY_01 = 'body-01',
    BODY_02 = 'body-02',
    BODY_03 = 'body-03',

    // Labels - Outfit
    LABEL_01 = 'label-01',
    LABEL_02 = 'label-02',

    // Buttons - Outfit
    BUTTON_01 = 'button-01',
    BUTTON_02 = 'button-02',

    // Captions / Meta - Outfit
    CAPTION_01 = 'caption-01',
    CAPTION_02 = 'caption-02',
}

interface TextProps {
    typography: Typography;
    children: ReactNode;
    className?: string;
    style?: React.CSSProperties;
}

export default function Text({
    typography,
    children,
    className = '',
    style = {},
}: TextProps) {
    return (
        <p
            className={`${typography} ${className} m-0`}
            style={style}
        >
            {children}
        </p>
    );
}
