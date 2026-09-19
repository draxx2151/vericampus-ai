import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { api } from '../services/api';

const ApplicationContext = createContext();

export const ApplicationProvider = ({ children }) => {
  const { token, currentUser, role } = useAuth();
  const [applications, setApplications] = useState([]);
  const [myApplication, setMyApplication] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchApplications = async () => {
    const savedToken = token || localStorage.getItem('vericampus_token');
    if (!savedToken) {
      setApplications([]);
      setMyApplication(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      if (role === 'STUDENT' || currentUser?.role === 'STUDENT') {
        const app = await api.getMyApplication(savedToken);
        setMyApplication(app);
        setApplications(app ? [app] : []);
      } else if (role === 'ADMIN' || currentUser?.role === 'ADMIN') {
        const apps = await api.getApplications(savedToken);
        setApplications(apps);
      }
    } catch (err) {
      console.error("Failed to load applications", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [token, role, currentUser]);

  const refreshState = async () => {
    await fetchApplications();
  };

  return (
    <ApplicationContext.Provider value={{
      applications,
      myApplication,
      notifications,
      loading,
      fetchApplications,
      refreshState,
      setApplications
    }}>
      {children}
    </ApplicationContext.Provider>
  );
};

export const useApplications = () => useContext(ApplicationContext);
