import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Users, AlertCircle } from 'lucide-react';
import { useToast } from '../context/ToastContext';

interface Team {
  id: string;
  name: string;
}

export default function Teams() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [newTeamName, setNewTeamName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();

  const fetchTeams = async () => {
    try {
      const response = await api.get('/teams/');
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
    setIsLoading(true);
    try {
      await api.post('/teams/', { name: newTeamName });
      setNewTeamName('');
      fetchTeams();
      addToast('Team created successfully', 'success');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create team');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Your Teams</h1>
              <p className="text-gray-500 mt-1">Manage your workspaces and collaborators.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-1 space-y-6">
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold text-gray-900">Create a team</h2>
                </CardHeader>
                <CardBody>
                  <form onSubmit={handleCreate} className="space-y-4">
                    {error && (
                      <div className="flex items-center p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded">
                        <AlertCircle size={16} className="mr-2 flex-shrink-0" />
                        <span>{error}</span>
                      </div>
                    )}
                    <Input
                      label="Team Name"
                      type="text"
                      placeholder="e.g. Engineering"
                      required
                      value={newTeamName}
                      onChange={(e) => setNewTeamName(e.target.value)}
                    />
                    <Button type="submit" className="w-full" disabled={isLoading}>
                      {isLoading ? 'Creating...' : 'Create Team'}
                    </Button>
                  </form>
                </CardBody>
              </Card>
            </div>

            <div className="md:col-span-2">
              <div className="grid gap-4 sm:grid-cols-2">
                {teams.map(team => (
                  <Card key={team.id} className="hover:shadow-md transition-shadow">
                    <Link to={`/teams/${team.id}`} className="block h-full">
                      <CardBody className="flex items-start">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 mr-4 flex-shrink-0">
                          <Users size={20} />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">{team.name}</h3>
                          <p className="text-sm text-blue-600 mt-1">View team →</p>
                        </div>
                      </CardBody>
                    </Link>
                  </Card>
                ))}
                
                {teams.length === 0 && (
                  <div className="sm:col-span-2 text-center py-12 bg-white border border-dashed border-gray-300 rounded-lg">
                    <Users size={32} className="mx-auto text-gray-400 mb-3" />
                    <p className="text-gray-500 mb-4">You aren't part of any teams yet.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
