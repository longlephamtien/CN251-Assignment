import React from 'react';
import { FormInput, Button } from '../common';

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
    <form onSubmit={onSubmit}>
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
        style={{width: '100%', marginBottom: '1rem'}}
      >
        {loading ? 'Please wait...' : (authMode === 'login' ? 'Login' : 'Register')}
      </Button>
      
      <div style={{textAlign: 'center'}}>
        <button 
          type="button" 
          className="btn btn-secondary" 
          onClick={onToggleMode}
          style={{background: 'none', color: 'var(--primary-blue)', textDecoration: 'underline'}}
        >
          {authMode === 'login' ? 'Need an account? Register' : 'Have an account? Login'}
        </button>
      </div>
    </form>
  );
}

export default ClientAuthForm;
