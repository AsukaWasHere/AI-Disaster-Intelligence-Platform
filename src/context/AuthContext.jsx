import React, { createContext, useState, useEffect } from 'react';
import { getMe } from '../services/api';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // Wait to check memory before rendering

  // Check if we have a saved token when the app first opens
  useEffect(() => {
    const token = localStorage.getItem('sentinel_token');
    if (token) {
      getMe(token)
        .then(userData => setUser(userData))
        .catch(() => {
          localStorage.removeItem('sentinel_token');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = (userData, token) => {
    localStorage.setItem('sentinel_token', token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('sentinel_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};