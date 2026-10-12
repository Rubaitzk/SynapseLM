import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import NewConversation from './pages/NewConversation';
import ChatsOverview from './pages/ChatsOverview';
import Teams from './pages/Teams';
import TeamDetails from './pages/TeamDetails';
import Invitations from './pages/Invitations';
import ConversationView from './pages/ConversationView';
import ShareAccept from './pages/ShareAccept';
import Settings from './pages/Settings';

import { ToastProvider } from './context/ToastContext';
import { NotificationProvider } from './context/NotificationContext';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  
  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  
  return <>{children}</>;
};

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <NotificationProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/" element={<ProtectedRoute><NewConversation /></ProtectedRoute>} />
              <Route path="/chats" element={<ProtectedRoute><ChatsOverview /></ProtectedRoute>} />
              <Route path="/teams" element={<ProtectedRoute><Teams /></ProtectedRoute>} />
              <Route path="/teams/:id" element={<ProtectedRoute><TeamDetails /></ProtectedRoute>} />
              <Route path="/conversations/:id" element={<ProtectedRoute><ConversationView /></ProtectedRoute>} />
              <Route path="/shares/:token" element={<ProtectedRoute><ShareAccept /></ProtectedRoute>} />
              <Route path="/invitations" element={<ProtectedRoute><Invitations /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            </Routes>
          </Router>
        </NotificationProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
