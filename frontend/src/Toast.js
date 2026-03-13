// Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
// SAM (Smart Analyst for Markets) — Proprietary Software

import React, { useState, useEffect, useCallback } from 'react';

let addToastGlobal = null;

export function showToast(message, type = 'info') {
  if (addToastGlobal) addToastGlobal({ message, type, id: Date.now() + Math.random() });
}

function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((toast) => {
    setToasts(prev => [...prev.slice(-4), toast]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== toast.id));
    }, 5000);
  }, []);

  useEffect(() => {
    addToastGlobal = addToast;
    return () => { addToastGlobal = null; };
  }, [addToast]);

  const dismiss = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`} onClick={() => dismiss(t.id)}>
          <span className="toast-icon">
            {t.type === 'alert' ? '\u26A0' : t.type === 'earnings' ? '\uD83D\uDCC5' : '\u2139'}
          </span>
          <span className="toast-msg">{t.message}</span>
          <button className="toast-close" onClick={(e) => { e.stopPropagation(); dismiss(t.id); }}>&times;</button>
        </div>
      ))}
    </div>
  );
}

export default ToastContainer;
