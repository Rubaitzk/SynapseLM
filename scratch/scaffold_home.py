import os

HOME_TSX = """import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { AppLayout } from '../components/layout/AppLayout';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Users, MessageSquare, Plus } from 'lucide-react';

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [teams, setTeams] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [invitations, setInvitations] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [teamsRes, convsRes, invRes] = await Promise.all([
          api.get('/teams/'),
          api.get('/conversations/'), // Assuming this endpoint exists, or handled elsewhere
          api.get('/invitations/')
        ].map(p => p.catch(e => ({ data: [] })))); // swallow errors for now
        
        setTeams(teamsRes.data);
        setConversations(convsRes.data);
        setInvitations(invRes.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, []);

  const handleCreateChat = async () => {
    // If there's an API to create a conversation directly
    // navigate to the new chat
  };

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.username}</h1>
              <p className="text-gray-500 mt-1">Here's what's happening in your workspace.</p>
            </div>
            <Button onClick={handleCreateChat}>
              <Plus size={18} className="mr-2" />
              New Chat
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <MessageSquare size={20} className="mr-2 text-blue-600" />
                  Recent Chats
                </h2>
                <Link to="/chats" className="text-sm text-blue-600 hover:underline">View all</Link>
              </CardHeader>
              <CardBody>
                {conversations.length > 0 ? (
                  <ul className="space-y-3">
                    {conversations.slice(0, 5).map((conv) => (
                      <li key={conv.id}>
                        <Link to={`/conversations/${conv.id}`} className="block hover:bg-gray-50 p-2 rounded -mx-2 transition-colors">
                          <div className="font-medium text-gray-900">{conv.name || 'Untitled Chat'}</div>
                          <div className="text-xs text-gray-500">Updated recently</div>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-center py-6">
                    <p className="text-sm text-gray-500 mb-4">No conversations yet</p>
                    <Button variant="secondary" size="sm" onClick={handleCreateChat}>Start a conversation</Button>
                  </div>
                )}
              </CardBody>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                    <Users size={20} className="mr-2 text-green-600" />
                    Your Teams
                  </h2>
                  <Link to="/teams" className="text-sm text-blue-600 hover:underline">View all</Link>
                </CardHeader>
                <CardBody>
                  {teams.length > 0 ? (
                    <ul className="space-y-3">
                      {teams.slice(0, 3).map((team) => (
                        <li key={team.id}>
                          <Link to={`/teams/${team.id}`} className="block hover:bg-gray-50 p-2 rounded -mx-2 transition-colors flex justify-between items-center">
                            <span className="font-medium text-gray-900">{team.name}</span>
                            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">View team</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-center py-6">
                      <p className="text-sm text-gray-500 mb-4">You aren't part of any teams yet.</p>
                      <Link to="/teams">
                        <Button variant="secondary" size="sm">Create Team</Button>
                      </Link>
                    </div>
                  )}
                </CardBody>
              </Card>

              {invitations.length > 0 && (
                <Card className="border-amber-200 bg-amber-50">
                  <CardHeader className="pb-2">
                    <h2 className="text-lg font-semibold text-amber-800">Pending Invitations</h2>
                  </CardHeader>
                  <CardBody>
                    <ul className="space-y-3">
                      {invitations.slice(0, 2).map((inv) => (
                        <li key={inv.id} className="flex justify-between items-center text-sm">
                          <span className="text-amber-900 font-medium">{inv.team_name}</span>
                          <Link to="/invitations" className="text-amber-700 hover:underline font-medium">Review</Link>
                        </li>
                      ))}
                    </ul>
                  </CardBody>
                </Card>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
"""

with open(r"D:\Hackathons\SynapseLM\frontend\src\pages\Home.tsx", "w") as f:
    f.write(HOME_TSX)

print("Updated Home.tsx")
