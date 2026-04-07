import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  // Destructure to get clean return object
  const { user, token, login, logout, loading } = context;
  return { user, token, login, logout, loading };
}