import { useState, useEffect } from 'react';
import api from '../lib/api';

export default function Invitations() {
  const [invitations, setInvitations] = useState<any[]>([]);

  const fetchInvitations = async () => {
    try {
      const response = await api.get('/invitations/');
      setInvitations(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, []);

  const handleAction = async (id: string, action: 'accept' | 'reject') => {
    try {
      await api.post(`/invitations/${id}/${action}`);
      fetchInvitations(); // refresh list
    } catch (err) {
      console.error('Action failed', err);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Pending Invitations</h2>
      <div className="space-y-4">
        {invitations.length === 0 && <p className="text-gray-500">No pending invitations.</p>}
        {invitations.map(inv => (
          <div key={inv.id} className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow border dark:border-gray-700 flex justify-between items-center">
            <div>
              <p className="font-semibold">Team: {inv.team_id}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Role: {inv.role}</p>
            </div>
            <div className="flex gap-2">
              <button 
                onClick={() => handleAction(inv.id, 'accept')}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Accept
              </button>
              <button 
                onClick={() => handleAction(inv.id, 'reject')}
                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
