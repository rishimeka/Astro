'use client';

import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  disabled?: boolean;
}

export default function Input({
  error = false,
  disabled = false,
  className = '',
  ...props
}: InputProps) {
  return (
    <input
      className={`input ${error ? 'input-error' : ''} ${disabled ? 'input-disabled' : ''} ${className}`}
      disabled={disabled}
      {...props}
    />
  );
}
