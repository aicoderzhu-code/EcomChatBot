import React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'prefix'> {
  label?: string;
  error?: string;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  clearable?: boolean;
  onClear?: () => void;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      error,
      prefix,
      suffix,
      clearable = false,
      onClear,
      type = 'text',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'w-full px-3 py-2 text-base bg-card-bg border border-border rounded-md transition-all duration-250 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed';

    const errorStyles = error ? 'border-error focus:ring-error focus:border-error' : '';

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-primary mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          {prefix && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary">
              {prefix}
            </div>
          )}
          <input
            ref={ref}
            type={type}
            className={cn(
              baseStyles,
              errorStyles,
              prefix && 'pl-10',
              (suffix || clearable) && 'pr-10',
              className
            )}
            disabled={disabled}
            {...props}
          />
          {clearable && props.value && !disabled && (
            <button
              type="button"
              onClick={onClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-tertiary hover:text-secondary transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          {suffix && !clearable && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-secondary">
              {suffix}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1.5 text-sm text-error">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
