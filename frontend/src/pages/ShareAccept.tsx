import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { useToast } from '../context/ToastContext';
import { Share2, Lock, ArrowRight, Loader2 } from 'lucide-react';

export default function ShareAccept() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [branching, setBranching] = useState(false);
  const [error, setError] = useState('');
  
  useEffect(() => {
    const fetchPreview = async () => {
      try {
        const res = await api.get(`/shares/${token}`);
        setPreview(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Invalid or expired share link");
      } finally {
        setLoading(false);
      }
    };
    fetchPreview();
  }, [token]);

  const handleRequestAccess = async () => {
    setRequesting(true);
    try {
      await api.post(`/shares/${token}/requests`);
      addToast("Access request sent. Waiting for approval.", "success");
      // Maybe navigate to a pending requests page or home
      navigate('/');
    } catch (err: any) {
      addToast(err.response?.data?.detail || "Failed to request access", "error");
    } finally {
      setRequesting(false);
    }
  };

  const handleBranch = async () => {
    setBranching(true);
    try {
      const res = await api.post(`/shares/${token}/branches`);
      addToast("Created a new branch of this conversation.", "success");
      navigate(`/conversations/${res.data.id}`);
    } catch (err: any) {
      if (err.response?.status === 400 && err.response?.data?.detail === "You are already a participant in this conversation") {
          // If already a participant, we could fetch the conversation ID if the backend returned it, but it didn't. 
          addToast("You are already a participant in this conversation.", "info");
      } else {
          addToast(err.response?.data?.detail || "Failed to create branch", "error");
      }
    } finally {
      setBranching(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <div className="flex-1 flex flex-col items-center justify-center max-w-md mx-auto text-center p-8">
          <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
            <Lock size={32} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600 mb-8">{error}</p>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex-1 flex flex-col items-center justify-center max-w-lg mx-auto text-center p-8">
        <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
          <Share2 size={32} />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Shared Conversation</h2>
        <p className="text-xl font-medium text-gray-800 mb-1">{preview.title}</p>
        <p className="text-gray-500 mb-8">Shared by {preview.owner_username}</p>
        
        <div className="flex flex-col sm:flex-row gap-4 w-full">
          <Button 
            className="flex-1" 
            variant="secondary"
            onClick={handleBranch}
            disabled={branching || requesting}
          >
            {branching ? 'Branching...' : 'Branch Conversation'}
          </Button>
          <Button 
            className="flex-1" 
            onClick={handleRequestAccess}
            disabled={requesting || branching}
          >
            {requesting ? 'Requesting...' : 'Request Access'}
            {!requesting && <ArrowRight className="ml-2 w-4 h-4" />}
          </Button>
        </div>
      </div>
    </AppLayout>
  );
}
