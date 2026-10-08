import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { useToast } from '../context/ToastContext';
import { Send, AlertCircle } from 'lucide-react';

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
          // Find personal team or just pick the first one
          const personalTeam = res.data.find((t: any) => t.name.toLowerCase() === 'personal team');
          setSelectedTeamId(personalTeam ? personalTeam.id : res.data[0].id);
        }
      } catch (err) {}
    };
    fetchTeams();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    if (teams.length === 0) {
      addToast('You must create a team first to start a conversation.', 'error');
      navigate('/teams');
      return;
    }
    if (!selectedTeamId) {
      addToast('Please select a team.', 'error');
      return;
    }
    
    setIsSubmitting(true);
    try {
      // 1. Create a draft conversation
      const convRes = await api.post('/conversations/', { 
        title: content.substring(0, 30) + (content.length > 30 ? '...' : ''), 
        team_id: selectedTeamId 
      });
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
                {teams.length > 0 ? (
                  <select 
                    value={selectedTeamId}
                    onChange={e => setSelectedTeamId(e.target.value)}
                    className="text-xs bg-gray-100 border-none rounded py-1 px-2 text-gray-600 focus:ring-0 outline-none cursor-pointer"
                  >
                    {teams.map(t => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                ) : (
                  <span className="text-xs text-amber-600 flex items-center">
                    <AlertCircle size={12} className="mr-1" />
                    No teams available
                  </span>
                )}
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
