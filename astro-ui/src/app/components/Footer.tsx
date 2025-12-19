"use client"

import React from 'react';

export default function Footer() {
    return (
        <footer className="site-footer">
            <div className="site-footer-inner">
                <div className="brand-row">
                    <img src="/astrix-logo.svg" alt="Astrix Labs logo" className="footer-logo" />
                    <div className="brand-text">
                        <div className="footer-name">Astrix Labs</div>
                        <div className="footer-copy">© 2026 Astrix Labs Inc. All rights reserved.</div>
                    </div>
                </div>
            </div>
        </footer>
    );
}
