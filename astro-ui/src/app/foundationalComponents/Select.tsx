'use client';

import React from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
  disabled?: boolean;
  options: Array<{ value: string; label: string }>;
}

export default function Select({
  error = false,
  disabled = false,
  options = [],
  className = '',
  ...props
}: SelectProps) {
  return (
    <select
      className={`select ${error ? 'select-error' : ''} ${disabled ? 'select-disabled' : ''} ${className}`}
      disabled={disabled}
      {...props}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
