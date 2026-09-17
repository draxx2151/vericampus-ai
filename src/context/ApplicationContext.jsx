import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const ApplicationContext = createContext();

export const ApplicationProvider = ({ children }) => {
  const [applications, setApplications] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchApplications = async () => {
    try {
      const data = await api.getApplications();
      setApplications(data);
    } catch (err) {
      console.error("Failed to load applications", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchNotifications = async (role, studentId) => {
    try {
      const notifs = await api.getNotifications(role, studentId);
      setNotifications(notifs);
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const refreshState = async () => {
    await fetchApplications();
  };

  return (
    <ApplicationContext.Provider value={{
      applications,
      notifications,
      loading,
      fetchApplications,
      fetchNotifications,
      refreshState,
      setApplications
    }}>
      {children}
    </ApplicationContext.Provider>
  );
};

export const useApplications = () => useContext(ApplicationContext);
