import React from 'react';
import { FormInput, Button } from '../common';
import './AdminLoginForm.css';

/**
 * AdminLoginForm Component
 */
function AdminLoginForm({ loginForm, setLoginForm, onSubmit, loading, onBack }) {
  return (
    <form onSubmit={onSubmit} className="admin-login-form">
      <FormInput
        label="Username"
        type="text"
        value={loginForm.username}
        onChange={(e) => setLoginForm({...loginForm, username: e.target.value})}
        required
      />
      
      <FormInput
        label="Password"
        type="password"
        value={loginForm.password}
        onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
        required
      />
      
      <FormInput
        label="Server IP"
        type="text"
        value={loginForm.server_ip}
        onChange={(e) => setLoginForm({...loginForm, server_ip: e.target.value})}
        placeholder="localhost or IP address"
      />
      
      <Button 
        type="submit" 
        variant="primary" 
        disabled={loading} 
        className="submit-button"
      >
        {loading ? 'Logging in...' : 'Login'}
      </Button>
    </form>
  );
}

export default AdminLoginForm;
