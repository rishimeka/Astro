'use client';

import React from 'react';

interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: boolean;
}

export default function Checkbox({
  label,
  error = false,
  disabled = false,
  className = '',
  id,
  ...props
}: CheckboxProps) {
  return (
    <div className={`checkbox-wrapper`}>
      <input
        id={id}
        type="checkbox"
        className={`checkbox ${error ? 'checkbox-error' : ''} ${disabled ? 'checkbox-disabled' : ''} ${className}`}
        disabled={disabled}
        {...props}
      />
      {label && <label htmlFor={id} className="checkbox-label">{label}</label>}
    </div>
  );
}
