import React, { createContext, useContext, useState, useEffect } from 'react';
import { DEMO_USERS } from '../data/mockData';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('vericampus_user');
    return saved ? JSON.parse(saved) : null;
  });

  const login = (role, userObject) => {
    const user = userObject || (role === 'ADMIN' ? DEMO_USERS.admin : DEMO_USERS.students[0]);
    setCurrentUser(user);
    localStorage.setItem('vericampus_user', JSON.stringify(user));
  };

  const logout = () => {
    setCurrentUser(null);
    localStorage.removeItem('vericampus_user');
  };

  return (
    <AuthContext.Provider value={{ currentUser, login, logout, role: currentUser?.role }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
