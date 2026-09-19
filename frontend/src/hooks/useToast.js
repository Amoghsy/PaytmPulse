import { useState, useCallback } from 'react';

let globalAddToast = null;

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((msgOrObj, type = 'info', duration = 4000) => {
    let message = msgOrObj;
    let toastType = type;
    let toastDuration = duration;

    if (typeof msgOrObj === 'object' && msgOrObj !== null) {
      message = msgOrObj.message || msgOrObj.text || '';
      toastType = msgOrObj.type || 'info';
      toastDuration = msgOrObj.duration !== undefined ? msgOrObj.duration : duration;
    }

    const id = Date.now() + Math.random().toString(36).substring(2, 7);
    const newToast = { id, message: String(message), type: toastType, duration: toastDuration };

    setToasts(prev => [...prev, newToast]);

    if (toastDuration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, toastDuration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  globalAddToast = addToast;

  return { toasts, addToast, showToast: addToast, removeToast };
}

export function showToast(message, type = 'info', duration = 4000) {
  if (globalAddToast) {
    globalAddToast(message, type, duration);
  } else {
    console.log(`[Toast ${type}]:`, message);
  }
}
