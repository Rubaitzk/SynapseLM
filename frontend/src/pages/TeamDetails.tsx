import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';

export default function TeamDetails() {
  const { id } = useParams<{ id: string }>();
  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchDetails = async () => {
    try {
      const [teamRes, membersRes] = await Promise.all([
        api.get(`/teams/${id}`),
        api.get(`/teams/${id}/members`)
      ]);
      setTeam(teamRes.data);
      setMembers(membersRes.data);
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

  if (!team) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <Link to="/teams" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Teams</Link>
        <h2 className="text-3xl font-bold">{team.name}</h2>
      </div>

      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border dark:border-gray-700">
        <h3 className="text-xl font-semibold mb-4">Invite Member</h3>
        {error && <div className="p-3 mb-4 text-sm text-red-500 bg-red-100 rounded">{error}</div>}
        {success && <div className="p-3 mb-4 text-sm text-green-700 bg-green-100 rounded">{success}</div>}
        
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
        <ul className="space-y-3">
          {members.map(m => (
            <li key={m.id} className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-900 rounded border dark:border-gray-700">
              <span>{m.user?.username || m.user_id}</span>
              <span className="px-2 py-1 text-xs font-semibold rounded bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 uppercase">
                {m.role}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
