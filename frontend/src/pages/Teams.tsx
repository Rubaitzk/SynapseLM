import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';

interface Team {
  id: string;
  name: string;
}

export default function Teams() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [newTeamName, setNewTeamName] = useState('');
  const [error, setError] = useState('');

  const fetchTeams = async () => {
    try {
      const response = await api.get('/teams');
      setTeams(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/teams/', { name: newTeamName });
      setNewTeamName('');
      fetchTeams();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create team');
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Your Teams</h2>
      
      <form onSubmit={handleCreate} className="mb-8 flex gap-4">
        <input
          type="text"
          placeholder="New Team Name"
          required
          className="flex-1 px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          value={newTeamName}
          onChange={(e) => setNewTeamName(e.target.value)}
        />
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Create Team
        </button>
      </form>
      
      {error && <div className="p-3 mb-4 text-sm text-red-500 bg-red-100 rounded">{error}</div>}

      <div className="grid gap-4 md:grid-cols-2">
        {teams.map(team => (
          <Link 
            key={team.id} 
            to={`/teams/${team.id}`}
            className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow border dark:border-gray-700 block"
          >
            <h3 className="text-xl font-semibold">{team.name}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Click to view details</p>
          </Link>
        ))}
        {teams.length === 0 && <p className="text-gray-500">You don't belong to any teams yet.</p>}
      </div>
    </div>
  );
}
