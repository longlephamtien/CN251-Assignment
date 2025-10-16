import React from 'react';

/**
 * Reusable Form Input Component
 */
function FormInput({ 
  label, 
  type = 'text', 
  value, 
  onChange, 
  placeholder, 
  required = false,
  disabled = false,
  helpText 
}) {
  return (
    <div className="form-group">
      {label && <label className="form-label">{label}{required && '*'}</label>}
      <input
        type={type}
        className="form-input"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
      />
      {helpText && <small className="text-gray">{helpText}</small>}
    </div>
  );
}

export default FormInput;
