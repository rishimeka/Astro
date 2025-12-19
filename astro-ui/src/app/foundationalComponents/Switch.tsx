'use client';

import React from 'react';

interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export default function Switch({
  label,
  disabled = false,
  className = '',
  id,
  ...props
}: SwitchProps) {
  return (
    <div className={`switch-wrapper`}>
      <input
        id={id}
        type="checkbox"
        className={`switch ${disabled ? 'switch-disabled' : ''} ${className}`}
        disabled={disabled}
        {...props}
      />
      <label htmlFor={id} className="switch-label"></label>
      {label && <span className="switch-text">{label}</span>}
    </div>
  );
}
