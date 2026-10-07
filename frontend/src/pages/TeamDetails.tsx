import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';

export default function TeamDetails() {
  const { id } = useParams<{ id: string }>();
  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [newConvTitle, setNewConvTitle] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

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
    setError('');
    setSuccess('');
    try {
      await api.post(`/teams/${id}/invitations`, { invitee_email: inviteEmail, role: 'member' });
      setInviteEmail('');
      setSuccess('Invitation sent successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send invitation');
    }
  };

  const handleCreateConv = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.post('/conversations/', { title: newConvTitle, team_id: id });
      setNewConvTitle('');
      setSuccess('Conversation created!');
      fetchDetails();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create conversation');
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!window.confirm("Remove this member from the team? They will also be removed from all conversations in this team.")) return;
    try {
      await api.delete(`/teams/${id}/members/${userId}`);
      fetchDetails();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to remove member');
    }
  };

  if (!team) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <Link to="/teams" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Teams</Link>
        <h2 className="text-3xl font-bold">{team.name}</h2>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border dark:border-gray-700">
        <h3 className="text-xl font-semibold mb-4">Conversations</h3>
        
        <form onSubmit={handleCreateConv} className="flex gap-4 mb-6">
          <input
            type="text"
            placeholder="New Conversation Title"
            required
            className="flex-1 px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            value={newConvTitle}
            onChange={(e) => setNewConvTitle(e.target.value)}
          />
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Create
          </button>
        </form>

        <div className="space-y-3">
          {conversations.length === 0 && <p className="text-gray-500">No conversations yet.</p>}
          {conversations.map(c => (
            <Link 
              key={c.id} 
              to={`/conversations/${c.id}`}
              className="block p-4 bg-gray-50 dark:bg-gray-900 rounded border dark:border-gray-700 hover:border-blue-500 transition-colors"
            >
              <h4 className="font-semibold text-lg">{c.title}</h4>
            </Link>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border dark:border-gray-700">
        <h3 className="text-xl font-semibold mb-4">Invite Member</h3>
        
        <form onSubmit={handleInvite} className="flex gap-4">
          <input
            type="email"
            placeholder="User Email"
            required
            className="flex-1 px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Send Invite
          </button>
        </form>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border dark:border-gray-700">
        <h3 className="text-xl font-semibold mb-4">Members</h3>
        {error && <div className="p-3 mb-4 text-sm text-red-500 bg-red-100 rounded">{error}</div>}
        {success && <div className="p-3 mb-4 text-sm text-green-700 bg-green-100 rounded">{success}</div>}
        <ul className="space-y-3">
          {members.map(m => (
            <li key={m.id} className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-900 rounded border dark:border-gray-700">
              <span>{m.user?.username || m.user_id}</span>
              <div className="flex items-center gap-4">
                <span className="px-2 py-1 text-xs font-semibold rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 uppercase">
                  {m.role}
                </span>
                <button 
                  onClick={() => handleRemoveMember(m.user_id)}
                  className="text-xs text-red-600 hover:text-red-800 font-semibold"
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
