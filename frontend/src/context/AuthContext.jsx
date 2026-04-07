import { createContext, useState, useEffect } from 'react';
import { getMe } from '../services/api';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true); // Wait to check memory before rendering

  // Check if we have a saved token when the app first opens
  useEffect(() => {
    const savedToken = localStorage.getItem('sentinel_token');
    if (savedToken) {
      getMe(savedToken)
        .then(userData => {
          setUser(userData);
          setToken(savedToken);
        })
        .catch(() => {
          localStorage.removeItem('sentinel_token');
          setUser(null);
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = (userData, accessToken) => {
    localStorage.setItem('sentinel_token', accessToken);
    setUser(userData);
    setToken(accessToken);
  };

  const logout = () => {
    localStorage.removeItem('sentinel_token');
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};