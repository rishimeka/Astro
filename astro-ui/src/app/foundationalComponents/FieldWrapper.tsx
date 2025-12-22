'use client';

import React, { ReactNode } from 'react';

interface FieldWrapperProps {
  label?: string;
  error?: string;
  helperText?: string;
  children: ReactNode;
  required?: boolean;
  className?: string;
}

export default function FieldWrapper({
  label,
  error,
  helperText,
  children,
  required = false,
  className = '',
}: FieldWrapperProps) {
  return (
    <div className={`field-wrapper ${className}`}>
      {label && (
        <label className="field-label">
          {label}
          {required && <span className="field-required">*</span>}
        </label>
      )}
      <div className="field-input-wrapper">
        {children}
      </div>
      {error && <div className="field-error">{error}</div>}
      {helperText && !error && <div className="field-helper">{helperText}</div>}
    </div>
  );
}
