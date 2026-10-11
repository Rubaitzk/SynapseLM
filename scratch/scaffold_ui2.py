import os

BASE_DIR = r"D:\Hackathons\SynapseLM\frontend\src\components"
UI_DIR = os.path.join(BASE_DIR, "ui")
LAYOUT_DIR = os.path.join(BASE_DIR, "layout")
CONTEXT_DIR = r"D:\Hackathons\SynapseLM\frontend\src\context"

os.makedirs(UI_DIR, exist_ok=True)
os.makedirs(LAYOUT_DIR, exist_ok=True)
os.makedirs(CONTEXT_DIR, exist_ok=True)

MODAL_TSX = """import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export function Modal({ isOpen, onClose, title, children, maxWidth = 'max-w-md' }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div 
        ref={modalRef} 
        className={`bg-white rounded-lg shadow-xl w-full ${maxWidth} max-h-[90vh] flex flex-col`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          {title && <h2 className="text-lg font-semibold text-gray-900">{title}</h2>}
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 focus:outline-none">
            <X size={20} />
          </button>
        </div>
        <div className="p-6 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
"""

TOAST_CONTEXT_TSX = """import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  addToast: (message: string, type: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: ToastType) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-start p-4 bg-white border rounded shadow-lg w-80 animate-in slide-in-from-bottom-5 fade-in duration-200`}
          >
            <div className="flex-shrink-0 mr-3 mt-0.5">
              {toast.type === 'success' && <CheckCircle className="text-green-500" size={18} />}
              {toast.type === 'error' && <AlertCircle className="text-red-500" size={18} />}
              {toast.type === 'info' && <Info className="text-blue-500" size={18} />}
            </div>
            <div className="flex-1 mr-2 text-sm text-gray-800">{toast.message}</div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-gray-400 hover:text-gray-600 focus:outline-none"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};
"""

LAYOUT_TSX = """import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { MessageSquare, Users, Settings, LogOut, Menu } from 'lucide-react';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const navItems = [
    { name: 'Chats', path: '/', icon: MessageSquare },
    { name: 'Teams', path: '/teams', icon: Users },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col md:flex-row">
      {/* Mobile Header */}
      <div className="md:hidden flex items-center justify-between bg-white border-b border-gray-200 px-4 py-3">
        <h1 className="text-xl font-bold text-blue-600">SynapseLM</h1>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-gray-600">
          <Menu size={24} />
        </button>
      </div>

      {/* Sidebar */}
      <div className={`${mobileMenuOpen ? 'block' : 'hidden'} md:flex flex-col w-full md:w-64 bg-white border-r border-gray-200 h-screen md:sticky top-0`}>
        <div className="p-4 hidden md:block">
          <h1 className="text-xl font-bold text-blue-600">SynapseLM</h1>
        </div>
        
        <div className="px-3 py-4">
          <Link to="/" className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 mb-6">
            + New Chat
          </Link>
          
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                    isActive 
                      ? 'bg-blue-50 text-blue-700' 
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <item.icon size={18} className="mr-3" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-auto p-4 border-t border-gray-200">
          <div className="flex items-center mb-4 px-2">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold mr-3">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="text-sm font-medium text-gray-900 truncate">
              {user?.username}
            </div>
          </div>
          <button 
            onClick={logout}
            className="flex items-center w-full px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100"
          >
            <LogOut size={18} className="mr-3" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {children}
      </main>
    </div>
  );
}
"""

with open(os.path.join(UI_DIR, "Modal.tsx"), "w") as f:
    f.write(MODAL_TSX)

with open(os.path.join(CONTEXT_DIR, "ToastContext.tsx"), "w") as f:
    f.write(TOAST_CONTEXT_TSX)

with open(os.path.join(LAYOUT_DIR, "AppLayout.tsx"), "w") as f:
    f.write(LAYOUT_TSX)

print("Created Modal, Toast Context, AppLayout")
