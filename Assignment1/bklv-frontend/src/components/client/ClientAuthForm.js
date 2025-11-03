import React from 'react';
import { FormInput, Button } from '../common';
import './ClientAuthForm.css';

/**
 * ClientAuthForm Component - Login or Register form
 */
function ClientAuthForm({ 
  authMode, 
  authForm, 
  setAuthForm, 
  onSubmit, 
  loading, 
  onToggleMode 
}) {
  return (
    <form onSubmit={onSubmit} className="client-auth-form">
      <FormInput
        label="Username"
        type="text"
        value={authForm.username}
        onChange={(e) => setAuthForm({...authForm, username: e.target.value})}
        placeholder="your_username"
        required
      />
      
      <FormInput
        label="Password"
        type="password"
        value={authForm.password}
        onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
        required
      />
      
      {authMode === 'register' && (
        <FormInput
          label="Display Name"
          type="text"
          value={authForm.display_name}
          onChange={(e) => setAuthForm({...authForm, display_name: e.target.value})}
          placeholder="Your Name"
        />
      )}
      
      <FormInput
        label="Server IP"
        type="text"
        value={authForm.server_ip}
        onChange={(e) => setAuthForm({...authForm, server_ip: e.target.value})}
      />
      
      <FormInput
        label="Server Port"
        type="number"
        value={authForm.server_port}
        onChange={(e) => setAuthForm({...authForm, server_port: e.target.value})}
      />
      
      <Button 
        type="submit" 
        variant="primary" 
        disabled={loading} 
        className="submit-button"
      >
        {loading ? 'Please wait...' : (authMode === 'login' ? 'Login' : 'Register')}
      </Button>
      
      <div className="toggle-mode-container">
        <button 
          type="button" 
          className="btn btn-secondary toggle-mode-button" 
          onClick={onToggleMode}
        >
          {authMode === 'login' ? 'Need an account? Register' : 'Have an account? Login'}
        </button>
      </div>
    </form>
  );
}

export default ClientAuthForm;
