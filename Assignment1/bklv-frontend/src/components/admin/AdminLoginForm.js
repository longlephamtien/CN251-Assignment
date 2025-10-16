import React from 'react';
import { FormInput, Button } from '../common';

/**
 * AdminLoginForm Component
 */
function AdminLoginForm({ loginForm, setLoginForm, onSubmit, loading, onBack }) {
  return (
    <form onSubmit={onSubmit}>
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
      
      <Button 
        type="submit" 
        variant="primary" 
        disabled={loading} 
        style={{width: '100%'}}
      >
        {loading ? 'Logging in...' : 'Login'}
      </Button>
    </form>
  );
}

export default AdminLoginForm;
