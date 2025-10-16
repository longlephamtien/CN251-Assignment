import React from 'react';

/**
 * Reusable Button Component
 */
function Button({ 
  children, 
  onClick, 
  variant = 'primary', 
  size = 'medium', 
  disabled = false,
  type = 'button',
  className = '',
  style = {}
}) {
  const classNames = [
    'btn',
    `btn-${variant}`,
    size !== 'medium' && `btn-${size}`,
    disabled && 'disabled',
    className
  ].filter(Boolean).join(' ');

  return (
    <button
      type={type}
      className={classNames}
      onClick={onClick}
      disabled={disabled}
      style={style}
    >
      {children}
    </button>
  );
}

export default Button;
