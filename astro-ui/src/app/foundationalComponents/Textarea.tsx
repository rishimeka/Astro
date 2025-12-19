'use client';

import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  disabled?: boolean;
}

export default function Textarea({
  error = false,
  disabled = false,
  className = '',
  ...props
}: TextareaProps) {
  return (
    <textarea
      className={`textarea ${error ? 'textarea-error' : ''} ${disabled ? 'textarea-disabled' : ''} ${className}`}
      disabled={disabled}
      {...props}
    />
  );
}
