import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import NewConversation from './pages/NewConversation';
import ChatsOverview from './pages/ChatsOverview';
import Teams from './pages/Teams';
import TeamDetails from './pages/TeamDetails';
import Invitations from './pages/Invitations';
import ConversationView from './pages/ConversationView';

import { ToastProvider } from './context/ToastContext';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();
  
  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!user) return <Navigate to="/login" />;
  
  return <>{children}</>;
};

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<ProtectedRoute><NewConversation /></ProtectedRoute>} />
            <Route path="/chats" element={<ProtectedRoute><ChatsOverview /></ProtectedRoute>} />
            <Route path="/teams" element={<ProtectedRoute><Teams /></ProtectedRoute>} />
            <Route path="/teams/:id" element={<ProtectedRoute><TeamDetails /></ProtectedRoute>} />
            <Route path="/conversations/:id" element={<ProtectedRoute><ConversationView /></ProtectedRoute>} />
            <Route path="/invitations" element={<ProtectedRoute><Invitations /></ProtectedRoute>} />
          </Routes>
        </Router>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
