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
      // Step 1: Create a branch of the conversation
      const branchRes = await api.post(`/shares/${token}/branches`);
      const branchId = branchRes.data.id;

      // Step 2: Request collaboration access via this branch
      await api.post(`/shares/${token}/requests`, { branch_conversation_id: branchId });
      addToast("Access requested! You can chat in your private branch while awaiting owner approval.", "success");
      navigate(`/conversations/${branchId}`);
    } catch (err: any) {
      if (err.response?.status === 400 && err.response?.data?.detail === "You are already a participant in this conversation") {
        addToast("You are already a participant in this conversation.", "info");
        if (preview?.conversation_id) {
          navigate(`/conversations/${preview.conversation_id}`);
        }
      } else {
        addToast(err.response?.data?.detail || "Failed to request access", "error");
      }
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
        addToast("You are already a participant in this conversation.", "info");
        if (preview?.conversation_id) {
          navigate(`/conversations/${preview.conversation_id}`);
        }
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
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Shared Conversation</h2>
        <p className="text-xl font-medium text-gray-800 mb-1">{preview.title}</p>
        <p className="text-gray-500 mb-2">Shared by {preview.owner_username}</p>
        {preview.expires_at && (
          <p className="text-xs text-amber-600 mb-6">
            Expires: {new Date(preview.expires_at).toLocaleString()}
          </p>
        )}

        {preview.is_participant && preview.conversation_id ? (
          <div className="w-full space-y-4 mt-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
              You are already an authorized participant in this conversation.
            </div>
            <Button className="w-full" onClick={() => navigate(`/conversations/${preview.conversation_id}`)}>
              Open Conversation
              <ArrowRight className="ml-2 w-4 h-4" />
            </Button>
          </div>
        ) : (
          <div className="w-full space-y-6 mt-4">
            <div className="text-xs text-gray-500 bg-gray-50 p-4 rounded-lg border border-gray-200 text-left space-y-1.5">
              <p><strong>Branch Conversation:</strong> Creates an isolated copy of this chat snapshot to experiment with AI without altering the original.</p>
              <p><strong>Request Access:</strong> Creates your branch and asks the owner for direct collaboration access on the main chat.</p>
            </div>

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
        )}
      </div>
    </AppLayout>
  );
}
