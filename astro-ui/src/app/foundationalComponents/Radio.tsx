'use client';

import React from 'react';

interface RadioProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: boolean;
}

export default function Radio({
  label,
  error = false,
  disabled = false,
  className = '',
  id,
  ...props
}: RadioProps) {
  return (
    <div className={`radio-wrapper`}>
      <input
        id={id}
        type="radio"
        className={`radio ${error ? 'radio-error' : ''} ${disabled ? 'radio-disabled' : ''} ${className}`}
        disabled={disabled}
        {...props}
      />
      {label && <label htmlFor={id} className="radio-label">{label}</label>}
    </div>
  );
}
