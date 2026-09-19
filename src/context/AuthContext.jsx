import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('vericampus_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [token, setToken] = useState(() => {
    return localStorage.getItem('vericampus_token') || null;
  });

  const [loading, setLoading] = useState(false);

  // Validate token and refresh profile from backend /auth/me on mount
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('vericampus_token');
      if (savedToken) {
        try {
          const profile = await api.getMe(savedToken);
          setCurrentUser(profile);
          localStorage.setItem('vericampus_user', JSON.stringify(profile));
        } catch (err) {
          console.error("Token verification failed:", err);
          logout();
        }
      }
    };
    initAuth();
  }, []);

  const login = (role, userObject, accessToken = null) => {
    setCurrentUser(userObject);
    localStorage.setItem('vericampus_user', JSON.stringify(userObject));
    if (accessToken) {
      setToken(accessToken);
      localStorage.setItem('vericampus_token', accessToken);
    }
  };

  const logout = () => {
    setCurrentUser(null);
    setToken(null);
    localStorage.removeItem('vericampus_user');
    localStorage.removeItem('vericampus_token');
  };

  return (
    <AuthContext.Provider value={{ currentUser, token, login, logout, role: currentUser?.role }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
