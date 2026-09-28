import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { api } from '../services/api';

const ApplicationContext = createContext();

export const ApplicationProvider = ({ children }) => {
  const { token, currentUser, role } = useAuth();
  const [applications, setApplications] = useState([]);
  const [myApplication, setMyApplication] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    const savedToken = token || localStorage.getItem('vericampus_token');
    if (!savedToken) {
      setNotifications([]);
      setUnreadCount(0);
      return [];
    }

    try {
      const data = await api.getNotifications(savedToken);
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
      return data.notifications || [];
    } catch (err) {
      console.error("Failed to load notifications", err);
      return [];
    }
  };

  const markNotificationAsRead = async (notificationId) => {
    const savedToken = token || localStorage.getItem('vericampus_token');
    if (!savedToken) return;
    try {
      await api.markNotificationAsRead(notificationId, savedToken);
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Failed to mark notification as read", err);
    }
  };

  const markAllNotificationsAsRead = async () => {
    const savedToken = token || localStorage.getItem('vericampus_token');
    if (!savedToken) return;
    try {
      await api.markAllNotificationsAsRead(savedToken);
      setNotifications(prev =>
        prev.map(n => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
      );
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all notifications as read", err);
    }
  };

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
    fetchNotifications();
  }, [token, role, currentUser]);

  const refreshState = async () => {
    await Promise.all([fetchApplications(), fetchNotifications()]);
  };

  return (
    <ApplicationContext.Provider value={{
      applications,
      myApplication,
      notifications,
      unreadCount,
      loading,
      fetchApplications,
      fetchNotifications,
      markNotificationAsRead,
      markAllNotificationsAsRead,
      refreshState,
      setApplications
    }}>
      {children}
    </ApplicationContext.Provider>
  );
};

export const useApplications = () => useContext(ApplicationContext);
