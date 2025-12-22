'use client';
import Button, { ButtonAppearance, ButtonEmphasis, ButtonSize } from '../foundationalComponents/Button';
import { useRequestAccess } from './RequestAccessContext';

export default function AppHeader() {
    const { open } = useRequestAccess();
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
                    onClick={() => open()}
                >
                    Get Access
                </Button>
            </div>
        </header>
    )
}