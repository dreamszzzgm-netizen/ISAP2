import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('isap_api_key'));

  const login = (key) => {
    localStorage.setItem('isap_api_key', key);
    setApiKey(key);
  };

  const logout = () => {
    localStorage.removeItem('isap_api_key');
    setApiKey(null);
  };

  const isAuthenticated = !!apiKey;

  return (
    <AuthContext.Provider value={{ apiKey, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
