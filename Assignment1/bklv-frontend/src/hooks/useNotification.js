/**
 * Custom hook for notifications
 */
import { useState } from 'react';

export const useNotification = () => {
  const [notification, setNotification] = useState({
    show: false,
    type: 'info',
    title: '',
    message: ''
  });

  const showNotification = (type, title, message) => {
    setNotification({ show: true, type, title, message });
  };

  const closeNotification = () => {
    setNotification({ ...notification, show: false });
  };

  return {
    notification,
    showNotification,
    closeNotification
  };
};
