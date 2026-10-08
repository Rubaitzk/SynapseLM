import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { useToast } from '../context/ToastContext';
import { Send } from 'lucide-react';

export default function NewConversation() {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [teams, setTeams] = useState<any[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  
  const navigate = useNavigate();
  const { addToast } = useToast();

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const res = await api.get('/teams/');
        setTeams(res.data);
        if (res.data.length > 0) {
          // We no longer auto-select a team, default is empty (Personal Chat)
        }
      } catch (err) {}
    };
    fetchTeams();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    
    setIsSubmitting(true);
    try {
      // 1. Create a draft conversation
      const convPayload: any = { 
        title: content.substring(0, 30) + (content.length > 30 ? '...' : '')
      };
      if (selectedTeamId) {
        convPayload.team_id = selectedTeamId;
      }
      const convRes = await api.post('/conversations/', convPayload);
      const convId = convRes.data.id;
      
      // 2. Send the first message
      await api.post(`/conversations/${convId}/messages`, { content });
      
      // 3. Navigate to it
      navigate(`/conversations/${convId}`);
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to start conversation.', 'error');
      setIsSubmitting(false);
    }
  };

  return (
    <AppLayout>
      <div className="flex-1 flex flex-col h-full bg-white relative">
        <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto w-full">
          <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">What can I help you with?</h1>
          
          <form onSubmit={handleSubmit} className="w-full relative shadow-sm border border-gray-200 rounded-2xl bg-white p-2">
            <textarea
              className="w-full resize-none bg-transparent outline-none p-3 max-h-48 overflow-y-auto"
              rows={3}
              placeholder="Message SynapseLM..."
              value={content}
              onChange={e => setContent(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e as any);
                }
              }}
            />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
              <div className="px-2 flex items-center">
                <select 
                  value={selectedTeamId}
                  onChange={e => setSelectedTeamId(e.target.value)}
                  className="text-xs bg-gray-100 border-none rounded py-1 px-2 text-gray-600 focus:ring-0 outline-none cursor-pointer"
                >
                  <option value="">Personal Chat</option>
                  {teams.length > 0 && (
                    <optgroup label="Teams">
                      {teams.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </optgroup>
                  )}
                </select>
              </div>
              <Button type="submit" size="sm" className="rounded-xl px-4" disabled={!content.trim() || isSubmitting}>
                {isSubmitting ? 'Starting...' : <Send size={16} />}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}
