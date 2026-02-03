'use client';

import { StatusBadge } from '@/components/StatusBadge';
import ThemeToggle from '@/components/ThemeToggle';
import { useTheme } from '@/context/ThemeContext';
import styles from './page.module.scss';

export default function DesignSystemPage() {
  const { theme } = useTheme();

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <h1 className="heading-01">Design System</h1>
          <ThemeToggle showLabel />
        </div>
        <p className="body-01" style={{ color: 'var(--text-secondary)' }}>
          A comprehensive guide to the Astrix Labs design tokens, typography, and components.
          Currently viewing: <strong>{theme}</strong> mode.
        </p>
      </header>

      <nav className={styles.nav}>
        <a href="#theme">Theme</a>
        <a href="#colors">Colors</a>
        <a href="#typography">Typography</a>
        <a href="#spacing">Spacing</a>
        <a href="#buttons">Buttons</a>
        <a href="#inputs">Inputs</a>
        <a href="#form-elements">Form Elements</a>
        <a href="#modal">Modal</a>
        <a href="#effects">Effects</a>
        <a href="#status">Status Badges</a>
      </nav>

      {/* Theme Section */}
      <section id="theme" className={styles.section}>
        <h2 className="heading-02">Theme</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          The app supports both dark and light themes. Theme preference is persisted in localStorage.
        </p>

        <h3 className="heading-03 mb-4">Theme Toggle Component</h3>
        <div className={styles.componentRow}>
          <ThemeToggle />
          <ThemeToggle showLabel />
          <ThemeToggle size="sm" />
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`import ThemeToggle from '@/components/ThemeToggle';
import { useTheme } from '@/context/ThemeContext';

// Component usage
<ThemeToggle />
<ThemeToggle showLabel />
<ThemeToggle size="sm" />

// Hook usage
const { theme, toggleTheme, setTheme } = useTheme();

// theme: 'dark' | 'light'
// toggleTheme: () => void
// setTheme: (theme: 'dark' | 'light') => void`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Implementation</h3>
        <div className={styles.tokenList}>
          <div className={styles.tokenRow}>
            <span className="body-02">Theme Attribute</span>
            <code className="code-01">data-theme=&quot;dark&quot; | &quot;light&quot;</code>
          </div>
          <div className={styles.tokenRow}>
            <span className="body-02">Applied To</span>
            <code className="code-01">&lt;html&gt; element</code>
          </div>
          <div className={styles.tokenRow}>
            <span className="body-02">Storage Key</span>
            <code className="code-01">astrix-theme</code>
          </div>
          <div className={styles.tokenRow}>
            <span className="body-02">Default</span>
            <code className="code-01">dark</code>
          </div>
        </div>
      </section>

      {/* Colors Section */}
      <section id="colors" className={styles.section}>
        <h2 className="heading-02">Colors</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Core color tokens used throughout the application.
        </p>

        <h3 className="heading-03 mb-4">Accent Colors</h3>
        <div className={styles.colorGrid}>
          <ColorSwatch name="--accent-primary" value="#6C72FF" />
          <ColorSwatch name="--accent-primary-hover" value="#5A60E8" />
          <ColorSwatch name="--accent-primary-active" value="#4A50D8" />
          <ColorSwatch name="--accent-primary-subtle" value="rgba(108, 114, 255, 0.1)" />
          <ColorSwatch name="--accent-danger" value="#FF5C5C" />
        </div>

        <h3 className="heading-03 mb-4 mt-8">Text Colors</h3>
        <div className={styles.colorGrid}>
          <ColorSwatch name="--text-primary" value="#FFFFFF" />
          <ColorSwatch name="--text-secondary" value="rgba(255, 255, 255, 0.7)" />
          <ColorSwatch name="--text-muted" value="rgba(255, 255, 255, 0.5)" />
        </div>

        <h3 className="heading-03 mb-4 mt-8">Background Colors</h3>
        <div className={styles.colorGrid}>
          <ColorSwatch name="--bg-primary" value="#0D1117" />
          <ColorSwatch name="--bg-elevated" value="rgba(20, 24, 30, 0.6)" />
          <ColorSwatch name="--bg-alert" value="rgba(10, 10, 10, 0.4)" />
          <ColorSwatch name="--bg-code" value="rgba(255, 255, 255, 0.04)" />
        </div>

        <h3 className="heading-03 mb-4 mt-8">Border Colors</h3>
        <div className={styles.colorGrid}>
          <ColorSwatch name="--border-default" value="rgba(255, 255, 255, 0.08)" />
          <ColorSwatch name="--border-strong" value="rgba(255, 255, 255, 0.12)" />
        </div>

        <h3 className="heading-03 mb-4 mt-8">Semantic Colors</h3>
        <div className={styles.colorGrid}>
          <ColorSwatch name="--color-success" value="#10B981" />
          <ColorSwatch name="--color-warning" value="#F59E0B" />
          <ColorSwatch name="--color-info" value="#3B82F6" />
        </div>
      </section>

      {/* Typography Section */}
      <section id="typography" className={styles.section}>
        <h2 className="heading-02">Typography</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Font families and type scale for consistent text styling.
        </p>

        <h3 className="heading-03 mb-4">Font Families</h3>
        <div className={styles.fontShowcase}>
          <div className={styles.fontCard}>
            <span className={styles.fontLabel}>Display (Libre Baskerville)</span>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: '24px' }}>
              The quick brown fox jumps over the lazy dog
            </span>
            <code className="code-01">var(--font-display)</code>
          </div>
          <div className={styles.fontCard}>
            <span className={styles.fontLabel}>Body (Outfit)</span>
            <span style={{ fontFamily: 'var(--font-body)', fontSize: '16px' }}>
              The quick brown fox jumps over the lazy dog
            </span>
            <code className="code-01">var(--font-body)</code>
          </div>
          <div className={styles.fontCard}>
            <span className={styles.fontLabel}>Mono (JetBrains Mono)</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px' }}>
              const fox = &apos;quick&apos;; // jumps over
            </span>
            <code className="code-01">var(--font-mono)</code>
          </div>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Heading Scale</h3>
        <div className={styles.typeScale}>
          <div className={styles.typeRow}>
            <span className="heading-01">Heading 01</span>
            <code className="code-01">.heading-01 — 48px (36px mobile)</code>
          </div>
          <div className={styles.typeRow}>
            <span className="heading-02">Heading 02</span>
            <code className="code-01">.heading-02 — 32px (28px mobile)</code>
          </div>
          <div className={styles.typeRow}>
            <span className="heading-03">Heading 03</span>
            <code className="code-01">.heading-03 — 24px (20px mobile)</code>
          </div>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Body & Label Scale</h3>
        <div className={styles.typeScale}>
          <div className={styles.typeRow}>
            <span className="body-01">Body 01 — Primary body text for paragraphs and descriptions</span>
            <code className="code-01">.body-01 — 16px</code>
          </div>
          <div className={styles.typeRow}>
            <span className="body-02">Body 02 — Secondary body text for smaller content</span>
            <code className="code-01">.body-02 — 14px</code>
          </div>
          <div className={styles.typeRow}>
            <span className="label-01">LABEL 01</span>
            <code className="code-01">.label-01 — 12px, uppercase</code>
          </div>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Code Styles</h3>
        <div className={styles.typeScale}>
          <div className={styles.typeRow}>
            <span className="code-01">const example = &apos;code-01&apos;;</span>
            <code className="code-01">.code-01 — 14px mono</code>
          </div>
          <div className={styles.typeRow}>
            <span>Inline code: <code className="code-style">example</code></span>
            <code className="code-01">.code-style — inline code</code>
          </div>
        </div>
      </section>

      {/* Spacing Section */}
      <section id="spacing" className={styles.section}>
        <h2 className="heading-02">Spacing</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Consistent spacing scale based on 4px increments.
        </p>

        <h3 className="heading-03 mb-4">Scale (0-10)</h3>
        <div className={styles.spacingScale}>
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
            <div key={n} className={styles.spacingRow}>
              <code className="code-01">{n}</code>
              <div className={styles.spacingBar} style={{ width: `${n * 4}px` }} />
              <span className="body-02">{n * 4}px</span>
              <code className="code-01">.m-{n} / .p-{n}</code>
            </div>
          ))}
        </div>

        <h3 className="heading-03 mb-4 mt-8">Utility Classes</h3>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`/* Margin */
.m-{0-10}    /* all sides */
.mt-{0-10}   /* top */
.mr-{0-10}   /* right */
.mb-{0-10}   /* bottom */
.ml-{0-10}   /* left */
.mx-{0-10}   /* horizontal */
.my-{0-10}   /* vertical */

/* Padding */
.p-{0-10}    /* all sides */
.pt-{0-10}   /* top */
.pr-{0-10}   /* right */
.pb-{0-10}   /* bottom */
.pl-{0-10}   /* left */
.px-{0-10}   /* horizontal */
.py-{0-10}   /* vertical */`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Section Tokens</h3>
        <div className={styles.tokenList}>
          <div className={styles.tokenRow}>
            <code className="code-01">--space-section-vertical</code>
            <span className="body-02">1rem (0.75rem mobile)</span>
          </div>
          <div className={styles.tokenRow}>
            <code className="code-01">--space-section-horizontal</code>
            <span className="body-02">2rem (1rem mobile)</span>
          </div>
          <div className={styles.tokenRow}>
            <code className="code-01">--space-card-padding</code>
            <span className="body-02">1.5rem</span>
          </div>
          <div className={styles.tokenRow}>
            <code className="code-01">--space-element-gap</code>
            <span className="body-02">1rem</span>
          </div>
        </div>
      </section>

      {/* Buttons Section */}
      <section id="buttons" className={styles.section}>
        <h2 className="heading-02">Buttons</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Button variants for different contexts and actions.
        </p>

        <h3 className="heading-03 mb-4">Colors</h3>
        <div className={styles.componentRow}>
          <button className="btn btn-primary btn-highlight">Primary</button>
          <button className="btn btn-black-and-white btn-highlight">Black & White</button>
          <button className="btn btn-success btn-highlight">Success</button>
          <button className="btn btn-error btn-highlight">Error</button>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`.btn.btn-primary.btn-highlight
.btn.btn-black-and-white.btn-highlight
.btn.btn-success.btn-highlight
.btn.btn-error.btn-highlight`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Variants</h3>
        <div className={styles.componentRow}>
          <button className="btn btn-primary btn-highlight">Highlight (Filled)</button>
          <button className="btn btn-primary btn-outline">Outline</button>
          <button className="btn btn-primary btn-subtle">Subtle</button>
          <button className="btn btn-primary btn-minimal">Minimal</button>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`.btn.btn-primary.btn-highlight  /* filled background */
.btn.btn-primary.btn-outline   /* border only */
.btn.btn-primary.btn-subtle    /* subtle background */
.btn.btn-primary.btn-minimal   /* text only */`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Sizes</h3>
        <div className={styles.componentRow} style={{ alignItems: 'center' }}>
          <button className="btn btn-primary btn-highlight btn-xs">XS</button>
          <button className="btn btn-primary btn-highlight btn-sm">SM</button>
          <button className="btn btn-primary btn-highlight btn-md">MD</button>
          <button className="btn btn-primary btn-highlight btn-lg">LG</button>
          <button className="btn btn-primary btn-highlight btn-xl">XL</button>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`.btn-xs   /* extra small */
.btn-sm   /* small */
.btn-md   /* medium (default) */
.btn-lg   /* large */
.btn-xl   /* extra large */`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">States</h3>
        <div className={styles.componentRow}>
          <button className="btn btn-primary btn-highlight">Default</button>
          <button className="btn btn-primary btn-highlight" disabled>Disabled</button>
        </div>
      </section>

      {/* Inputs Section */}
      <section id="inputs" className={styles.section}>
        <h2 className="heading-02">Inputs</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Text input and textarea components.
        </p>

        <h3 className="heading-03 mb-4">Text Input</h3>
        <div className={styles.componentColumn}>
          <div className="field-wrapper">
            <label className="field-label">Default Input</label>
            <input type="text" className="input" placeholder="Enter text..." />
          </div>
          <div className="field-wrapper">
            <label className="field-label">
              Required Field <span className="field-required">*</span>
            </label>
            <input type="text" className="input" placeholder="Required..." />
            <span className="field-helper">This field is required</span>
          </div>
          <div className="field-wrapper">
            <label className="field-label">Error State</label>
            <input type="text" className="input input-error" defaultValue="Invalid value" />
            <span className="field-error">Please enter a valid value</span>
          </div>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<div className="field-wrapper">
  <label className="field-label">Label</label>
  <input type="text" className="input" />
  <span className="field-helper">Helper text</span>
</div>

/* Error state */
<input className="input input-error" />
<span className="field-error">Error message</span>`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Textarea</h3>
        <div className={styles.componentColumn}>
          <div className="field-wrapper">
            <label className="field-label">Description</label>
            <textarea className="textarea" placeholder="Enter description..." rows={3} />
          </div>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<textarea className="textarea" placeholder="..." />`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Select</h3>
        <div className={styles.componentColumn}>
          <div className="field-wrapper">
            <label className="field-label">Select Option</label>
            <select className="select">
              <option>Option 1</option>
              <option>Option 2</option>
              <option>Option 3</option>
            </select>
          </div>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<select className="select">
  <option>Option 1</option>
  ...
</select>`}</pre>
        </div>
      </section>

      {/* Form Elements Section */}
      <section id="form-elements" className={styles.section}>
        <h2 className="heading-02">Form Elements</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Checkboxes, switches, and radio buttons.
        </p>

        <h3 className="heading-03 mb-4">Checkbox</h3>
        <div className={styles.componentColumn}>
          <label className="checkbox-wrapper">
            <input type="checkbox" className="checkbox" defaultChecked />
            <span className="checkbox-label">Checked option</span>
          </label>
          <label className="checkbox-wrapper">
            <input type="checkbox" className="checkbox" />
            <span className="checkbox-label">Unchecked option</span>
          </label>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<label className="checkbox-wrapper">
  <input type="checkbox" className="checkbox" />
  <span className="checkbox-label">Label</span>
</label>`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Switch</h3>
        <div className={styles.componentColumn}>
          <label className="switch-wrapper">
            <input type="checkbox" className="switch" defaultChecked />
            <span className="switch-slider" />
            <span className="switch-text">Enabled</span>
          </label>
          <label className="switch-wrapper">
            <input type="checkbox" className="switch" />
            <span className="switch-slider" />
            <span className="switch-text">Disabled</span>
          </label>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<label className="switch-wrapper">
  <input type="checkbox" className="switch" />
  <span className="switch-slider" />
  <span className="switch-text">Label</span>
</label>`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Radio</h3>
        <div className={styles.componentColumn}>
          <label className="radio-wrapper">
            <input type="radio" className="radio" name="demo-radio" defaultChecked />
            <span className="radio-label">Option A</span>
          </label>
          <label className="radio-wrapper">
            <input type="radio" className="radio" name="demo-radio" />
            <span className="radio-label">Option B</span>
          </label>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<label className="radio-wrapper">
  <input type="radio" className="radio" name="group" />
  <span className="radio-label">Label</span>
</label>`}</pre>
        </div>
      </section>

      {/* Modal Section */}
      <section id="modal" className={styles.section}>
        <h2 className="heading-02">Modal</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Dialog/modal overlay pattern.
        </p>

        <h3 className="heading-03 mb-4">Structure</h3>
        <div className={styles.modalPreview}>
          <div className={styles.modalMock}>
            <div className={styles.modalMockHeader}>
              <span>Modal Title</span>
              <span className={styles.modalMockClose}>×</span>
            </div>
            <div className={styles.modalMockBody}>
              Modal content goes here. This can include forms, text, or any other content.
            </div>
            <div className={styles.modalMockFooter}>
              <button className="btn btn-primary btn-outline btn-sm">Cancel</button>
              <button className="btn btn-primary btn-highlight btn-sm">Confirm</button>
            </div>
          </div>
        </div>
        <div className={styles.codeBlock}>
          <pre className="code-01">{`<div className="modal-overlay">
  <div className="modal-container">
    <div className="modal-header">
      <h2>Title</h2>
      <button className="modal-close">×</button>
    </div>
    <div className="modal-body">
      Content
    </div>
    <div className="modal-footer">
      <button>Cancel</button>
      <button>Confirm</button>
    </div>
  </div>
</div>`}</pre>
        </div>
      </section>

      {/* Effects Section */}
      <section id="effects" className={styles.section}>
        <h2 className="heading-02">Effects & Radius</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Border radius and shadow tokens.
        </p>

        <h3 className="heading-03 mb-4">Border Radius</h3>
        <div className={styles.radiusGrid}>
          <div className={styles.radiusCard} style={{ borderRadius: 'var(--radius-sm)' }}>
            <code className="code-01">--radius-sm</code>
            <span className="body-02">6px</span>
          </div>
          <div className={styles.radiusCard} style={{ borderRadius: 'var(--radius-md)' }}>
            <code className="code-01">--radius-md</code>
            <span className="body-02">10px</span>
          </div>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Shadows</h3>
        <div className={styles.shadowGrid}>
          <div className={styles.shadowCard} style={{ boxShadow: 'var(--shadow-card)' }}>
            <code className="code-01">--shadow-card</code>
          </div>
          <div className={styles.shadowCard} style={{ boxShadow: 'var(--shadow-accent)' }}>
            <code className="code-01">--shadow-accent</code>
          </div>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Backdrop</h3>
        <div className={styles.tokenList}>
          <div className={styles.tokenRow}>
            <code className="code-01">--backdrop-blur</code>
            <span className="body-02">blur(10px)</span>
          </div>
        </div>
      </section>

      {/* Status Badges Section */}
      <section id="status" className={styles.section}>
        <h2 className="heading-02">Status Badges</h2>
        <p className="body-01 mb-6" style={{ color: 'var(--text-secondary)' }}>
          Status indicator badges used in runs and execution views.
        </p>

        <h3 className="heading-03 mb-4">Default Size (md)</h3>
        <div className={styles.statusGrid}>
          <StatusBadge status="running" />
          <StatusBadge status="completed" />
          <StatusBadge status="failed" />
          <StatusBadge status="pending" />
          <StatusBadge status="awaiting_confirmation" />
          <StatusBadge status="cancelled" />
        </div>

        <h3 className="heading-03 mb-4 mt-8">Small Size (sm)</h3>
        <div className={styles.statusGrid}>
          <StatusBadge status="running" size="sm" />
          <StatusBadge status="completed" size="sm" />
          <StatusBadge status="failed" size="sm" />
          <StatusBadge status="pending" size="sm" />
          <StatusBadge status="awaiting_confirmation" size="sm" />
          <StatusBadge status="cancelled" size="sm" />
        </div>

        <div className={styles.codeBlock}>
          <pre className="code-01">{`import StatusBadge from '@/components/StatusBadge/StatusBadge';

<StatusBadge status="running" />
<StatusBadge status="completed" />
<StatusBadge status="failed" />
<StatusBadge status="pending" />
<StatusBadge status="awaiting_confirmation" />
<StatusBadge status="cancelled" />

/* Sizes */
<StatusBadge status="running" size="md" />  {/* default */}
<StatusBadge status="running" size="sm" />`}</pre>
        </div>

        <h3 className="heading-03 mb-4 mt-8">Features</h3>
        <div className={styles.tokenList}>
          <div className={styles.tokenRow}>
            <span className="body-02">Animated dot</span>
            <span className="body-02" style={{ color: 'var(--text-muted)' }}>Running & Awaiting states have pulsing dot</span>
          </div>
          <div className={styles.tokenRow}>
            <span className="body-02">Squared corners</span>
            <span className="body-02" style={{ color: 'var(--text-muted)' }}>Uses --radius-sm (6px)</span>
          </div>
          <div className={styles.tokenRow}>
            <span className="body-02">Semantic colors</span>
            <span className="body-02" style={{ color: 'var(--text-muted)' }}>Info, success, danger, warning, muted</span>
          </div>
        </div>
      </section>
    </div>
  );
}

function ColorSwatch({ name, value }: { name: string; value: string }) {
  return (
    <div className={styles.colorSwatch}>
      <div
        className={styles.colorPreview}
        style={{ backgroundColor: value }}
      />
      <div className={styles.colorInfo}>
        <code className="code-01">{name}</code>
        <span className="body-02" style={{ color: 'var(--text-muted)' }}>{value}</span>
      </div>
    </div>
  );
}
