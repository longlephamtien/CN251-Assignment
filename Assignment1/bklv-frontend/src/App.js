import React, { useState } from 'react';
import './App.css';
import { LandingScreen, AdminDashboardScreen, ClientInterfaceScreen } from './screens';

function App() {
  const [mode, setMode] = useState('landing'); // 'landing', 'admin', 'client'

  return (
    <div className="App">
      {mode === 'landing' && <LandingScreen setMode={setMode} />}
      {mode === 'admin' && <AdminDashboardScreen onBack={() => setMode('landing')} />}
      {mode === 'client' && <ClientInterfaceScreen onBack={() => setMode('landing')} />}
    </div>
  );
}

export default App;
