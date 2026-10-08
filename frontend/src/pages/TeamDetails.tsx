import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { useToast } from '../context/ToastContext';
import { Modal } from '../components/ui/Modal';
import { MessageSquare, Users, ChevronRight, UserMinus } from 'lucide-react';

export default function TeamDetails() {
  const { id } = useParams<{ id: string }>();
  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  
  const [inviteEmail, setInviteEmail] = useState('');
  const [newConvTitle, setNewConvTitle] = useState('');
  const [isInviting, setIsInviting] = useState(false);
  const [isCreatingConv, setIsCreatingConv] = useState(false);
  
  const [memberToRemove, setMemberToRemove] = useState<any>(null);
  const { addToast } = useToast();

  const fetchDetails = async () => {
    try {
      const [teamRes, membersRes, convRes] = await Promise.all([
        api.get(`/teams/${id}`),
        api.get(`/teams/${id}/members`),
        api.get(`/teams/${id}/conversations`)
      ]);
      setTeam(teamRes.data);
      setMembers(membersRes.data);
      setConversations(convRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [id]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsInviting(true);
    try {
      await api.post(`/teams/${id}/invitations`, { invitee_email: inviteEmail, role: 'member' });
      setInviteEmail('');
      addToast('Invitation sent successfully!', 'success');
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to send invitation', 'error');
    } finally {
      setIsInviting(false);
    }
  };

  const handleCreateConv = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreatingConv(true);
    try {
      await api.post('/conversations/', { title: newConvTitle, team_id: id });
      setNewConvTitle('');
      addToast('Conversation created!', 'success');
      fetchDetails();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to create conversation', 'error');
    } finally {
      setIsCreatingConv(false);
    }
  };

  const confirmRemoveMember = async () => {
    if (!memberToRemove) return;
    try {
      await api.delete(`/teams/${id}/members/${memberToRemove.user_id}`);
      addToast('Member removed', 'success');
      setMemberToRemove(null);
      fetchDetails();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to remove member', 'error');
      setMemberToRemove(null);
    }
  };

  if (!team) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full text-gray-500">Loading team details...</div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-5xl mx-auto space-y-6">
          
          <nav className="flex items-center text-sm text-gray-500">
            <Link to="/teams" className="hover:text-gray-900 transition-colors">Teams</Link>
            <ChevronRight size={16} className="mx-2" />
            <span className="text-gray-900 font-medium">{team.name}</span>
          </nav>

          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">{team.name}</h1>
            <div className="flex gap-4 text-sm text-gray-500">
              <span className="flex items-center"><Users size={16} className="mr-1" /> {members.length} members</span>
              <span className="flex items-center"><MessageSquare size={16} className="mr-1" /> {conversations.length} chats</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              
              <Card>
                <CardHeader className="flex justify-between items-center pb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
                </CardHeader>
                <CardBody className="pt-0">
                  <form onSubmit={handleCreateConv} className="flex gap-3 mb-6">
                    <Input
                      placeholder="New conversation title..."
                      value={newConvTitle}
                      onChange={(e) => setNewConvTitle(e.target.value)}
                      required
                      className="flex-1"
                    />
                    <Button type="submit" disabled={isCreatingConv}>
                      {isCreatingConv ? 'Creating...' : 'Create'}
                    </Button>
                  </form>

                  {conversations.length > 0 ? (
                    <div className="border border-gray-200 rounded-lg overflow-hidden divide-y divide-gray-100">
                      {conversations.map(c => (
                        <Link 
                          key={c.id} 
                          to={`/conversations/${c.id}`}
                          className="flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-center">
                            <MessageSquare size={18} className="text-blue-500 mr-3" />
                            <span className="font-medium text-gray-900">{c.title || 'Untitled'}</span>
                          </div>
                          <ChevronRight size={18} className="text-gray-400" />
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                      <p className="text-gray-500 text-sm">No conversations yet.</p>
                    </div>
                  )}
                </CardBody>
              </Card>

            </div>
            
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold text-gray-900">Invite Member</h2>
                </CardHeader>
                <CardBody>
                  <form onSubmit={handleInvite} className="space-y-4">
                    <Input
                      placeholder="Email address"
                      type="email"
                      required
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                    />
                    <Button type="submit" className="w-full" variant="secondary" disabled={isInviting}>
                      {isInviting ? 'Sending...' : 'Send Invite'}
                    </Button>
                  </form>
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                    Members ({members.length})
                  </h2>
                </CardHeader>
                <CardBody className="p-0">
                  <ul className="divide-y divide-gray-100">
                    {members.map(m => (
                      <li key={m.id} className="p-4 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-900 text-sm">{m.user?.username || m.user_id}</div>
                          <div className="text-xs text-gray-500 uppercase mt-0.5">{m.role}</div>
                        </div>
                        <button 
                          onClick={() => setMemberToRemove(m)}
                          className="text-gray-400 hover:text-red-600 transition-colors"
                          title="Remove member"
                        >
                          <UserMinus size={18} />
                        </button>
                      </li>
                    ))}
                  </ul>
                </CardBody>
              </Card>
            </div>
          </div>
        </div>
      </div>

      <Modal 
        isOpen={!!memberToRemove} 
        onClose={() => setMemberToRemove(null)}
        title="Remove Member?"
      >
        <p className="text-gray-600 mb-6">
          Are you sure you want to remove <span className="font-semibold">{memberToRemove?.user?.username}</span> from the team? They will immediately lose access to all team conversations.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={() => setMemberToRemove(null)}>Cancel</Button>
          <Button variant="danger" onClick={confirmRemoveMember}>Remove Member</Button>
        </div>
      </Modal>

    </AppLayout>
  );
}
