'use client';

import React from 'react';

interface SliderProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export default function Slider({
  error = false,
  disabled = false,
  className = '',
  min = 0,
  max = 100,
  step = 1,
  ...props
}: SliderProps) {
  return (
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      className={`slider ${error ? 'slider-error' : ''} ${disabled ? 'slider-disabled' : ''} ${className}`}
      disabled={disabled}
      {...props}
    />
  );
}
