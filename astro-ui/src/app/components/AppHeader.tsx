'use client';
import Button, { ButtonAppearance, ButtonEmphasis, ButtonSize } from '../foundationalComponents/Button';

export default function AppHeader() {
    return (
        <header className="app-header">
            <div className="app-header-content">
                <div className="app-header-logo-section">
                    <img src="/astrix-logo.svg" alt="Astrix Labs" className="app-header-logo" />
                    <span className="app-header-company-name">Astrix Labs</span>
                </div>
                <div className="app-header-spacer"></div>
                <Button 
                    appearance={ButtonAppearance.PRIMARY} 
                    emphasis={ButtonEmphasis.HIGHLIGHT}
                    size={ButtonSize.SM}
                >
                    Get Access
                </Button>
            </div>
        </header>
    )
}