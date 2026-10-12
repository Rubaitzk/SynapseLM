import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import type { TeamInvitation } from '../context/NotificationContext';
import { Modal } from '../components/ui/Modal';
import { 
  MessageSquare, 
  Users, 
  ChevronRight, 
  UserMinus, 
  Mail, 
  Clock, 
  Check, 
  X, 
  AlertCircle, 
  Ban,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';

type InvitationFilter = 'all' | 'pending' | 'accepted' | 'declined' | 'cancelled' | 'expired';

export default function TeamDetails() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { subscribeToEvents } = useNotifications();
  const { addToast } = useToast();

  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [teamInvitations, setTeamInvitations] = useState<TeamInvitation[]>([]);
  const [invitationsLoading, setInvitationsLoading] = useState(false);
  const [invitationFilter, setInvitationFilter] = useState<InvitationFilter>('all');
  
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'member' | 'admin'>('member');
  const [newConvTitle, setNewConvTitle] = useState('');
  const [isInviting, setIsInviting] = useState(false);
  const [isCreatingConv, setIsCreatingConv] = useState(false);
  
  const [memberToRemove, setMemberToRemove] = useState<any>(null);
  const [invitationToCancel, setInvitationToCancel] = useState<TeamInvitation | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  const fetchDetails = useCallback(async () => {
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
  }, [id]);

  const fetchInvitations = useCallback(async () => {
    if (!id) return;
    try {
      setInvitationsLoading(true);
      const filterParam = invitationFilter === 'all' ? '' : `?status=${invitationFilter}`;
      const res = await api.get(`/teams/${id}/invitations${filterParam}`);
      setTeamInvitations(res.data);
    } catch (err: any) {
      // If user isn't admin/owner, 403 is expected
      if (err.response?.status !== 403) {
        console.error('Failed to load team invitations', err);
      }
    } finally {
      setInvitationsLoading(false);
    }
  }, [id, invitationFilter]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  useEffect(() => {
    fetchInvitations();
  }, [fetchInvitations]);

  // Realtime updates on team events
  useEffect(() => {
    const unsubscribe = subscribeToEvents((event) => {
      if (event.team_id === id || event.event?.startsWith('team.')) {
        fetchDetails();
        fetchInvitations();
      }
    });
    return unsubscribe;
  }, [subscribeToEvents, id, fetchDetails, fetchInvitations]);

  const currentMembership = members.find(m => m.user_id === user?.id || m.user?.id === user?.id);
  const isOwnerOrAdmin = currentMembership?.role === 'owner' || currentMembership?.role === 'admin';

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsInviting(true);
    try {
      await api.post(`/teams/${id}/invitations`, { 
        invitee_email: inviteEmail.trim(), 
        role: inviteRole 
      });
      setInviteEmail('');
      addToast('Invitation sent successfully!', 'success');
      fetchInvitations();
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

  const confirmCancelInvitation = async () => {
    if (!invitationToCancel) return;
    setIsCancelling(true);
    try {
      await api.post(`/teams/${id}/invitations/${invitationToCancel.id}/cancel`);
      addToast(`Invitation to ${invitationToCancel.invitee_email} cancelled`, 'success');
      setInvitationToCancel(null);
      fetchInvitations();
    } catch (err: any) {
      addToast(err.response?.data?.detail || 'Failed to cancel invitation', 'error');
    } finally {
      setIsCancelling(false);
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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            <Clock size={11} className="mr-1" /> Pending
          </span>
        );
      case 'accepted':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <Check size={11} className="mr-1" /> Accepted
          </span>
        );
      case 'rejected':
      case 'declined':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            <X size={11} className="mr-1" /> Declined
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
            <Ban size={11} className="mr-1" /> Cancelled
          </span>
        );
      case 'expired':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
            <AlertCircle size={11} className="mr-1" /> Expired
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">
            {status}
          </span>
        );
    }
  };

  if (!team) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2"></div>
          Loading team details...
        </div>
      </AppLayout>
    );
  }

  const pendingCount = teamInvitations.filter(i => i.status === 'pending').length;

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-gray-50/30">
        <div className="max-w-6xl mx-auto space-y-6">
          
          {/* Breadcrumb */}
          <nav className="flex items-center text-sm text-gray-500">
            <Link to="/teams" className="hover:text-gray-900 transition-colors">Teams</Link>
            <ChevronRight size={16} className="mx-2" />
            <span className="text-gray-900 font-medium">{team.name}</span>
          </nav>

          {/* Header Title */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{team.name}</h1>
              <p className="text-sm text-gray-500 mt-1">
                Collaborative workspace for shared chats, models, and team members.
              </p>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-600">
              <span className="flex items-center bg-white px-3 py-1.5 rounded-lg border border-gray-200 shadow-xs">
                <Users size={16} className="mr-1.5 text-blue-600" /> {members.length} members
              </span>
              <span className="flex items-center bg-white px-3 py-1.5 rounded-lg border border-gray-200 shadow-xs">
                <MessageSquare size={16} className="mr-1.5 text-indigo-600" /> {conversations.length} chats
              </span>
              {isOwnerOrAdmin && pendingCount > 0 && (
                <span className="flex items-center bg-amber-50 text-amber-800 px-3 py-1.5 rounded-lg border border-amber-200 shadow-xs font-medium">
                  <Mail size={16} className="mr-1.5 text-amber-600" /> {pendingCount} pending invite{pendingCount > 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column (Conversations & Invitations Management) */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Conversations Card */}
              <Card className="bg-white border-gray-200">
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
                      {isCreatingConv ? 'Creating...' : 'Create Chat'}
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
                      <p className="text-gray-500 text-sm">No conversations in this team yet.</p>
                    </div>
                  )}
                </CardBody>
              </Card>

              {/* Sender Invitation Management Dashboard */}
              {isOwnerOrAdmin && (
                <Card className="bg-white border-gray-200">
                  <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3">
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                        <Mail size={18} className="mr-2 text-blue-600" />
                        Team Invitations Dashboard
                      </h2>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Track sent invitations, view statuses, and cancel pending invites.
                      </p>
                    </div>
                    <button
                      onClick={() => fetchInvitations()}
                      className="inline-flex items-center text-xs font-medium text-gray-500 hover:text-gray-800 bg-gray-50 hover:bg-gray-100 px-2.5 py-1.5 rounded-lg border border-gray-200 transition-colors self-start sm:self-auto"
                      title="Refresh invitations"
                    >
                      <RefreshCw size={13} className={`mr-1.5 ${invitationsLoading ? 'animate-spin' : ''}`} />
                      Refresh
                    </button>
                  </CardHeader>
                  <CardBody className="pt-0 space-y-4">
                    {/* Status Filter Tabs */}
                    <div className="flex overflow-x-auto border-b border-gray-100 gap-1 pb-1 scrollbar-none text-xs">
                      {(['all', 'pending', 'accepted', 'declined', 'cancelled', 'expired'] as InvitationFilter[]).map((filter) => {
                        const isActive = invitationFilter === filter;
                        return (
                          <button
                            key={filter}
                            onClick={() => setInvitationFilter(filter)}
                            className={`px-3 py-1.5 rounded-lg font-medium capitalize transition-colors ${
                              isActive
                                ? 'bg-blue-50 text-blue-700 font-semibold'
                                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                            }`}
                          >
                            {filter}
                          </button>
                        );
                      })}
                    </div>

                    {/* Invitations Table / List */}
                    {invitationsLoading ? (
                      <div className="py-12 text-center text-gray-500 text-sm">
                        <div className="inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-2"></div>
                        <p>Loading invitations...</p>
                      </div>
                    ) : teamInvitations.length === 0 ? (
                      <div className="text-center py-10 bg-gray-50 rounded-lg border border-dashed border-gray-200">
                        <Mail size={32} className="mx-auto text-gray-300 mb-2" />
                        <p className="text-sm font-medium text-gray-700">No invitations found</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {invitationFilter === 'all'
                            ? 'Use the invite form on the right to add team members.'
                            : `No invitations with status "${invitationFilter}".`}
                        </p>
                      </div>
                    ) : (
                      <div className="border border-gray-200 rounded-lg overflow-x-auto">
                        <table className="w-full text-left text-xs text-gray-600 divide-y divide-gray-200">
                          <thead className="bg-gray-50 text-gray-700 font-semibold">
                            <tr>
                              <th className="px-4 py-3">Invitee</th>
                              <th className="px-3 py-3">Role</th>
                              <th className="px-3 py-3">Status</th>
                              <th className="px-3 py-3">Sent</th>
                              <th className="px-3 py-3">Expires</th>
                              <th className="px-4 py-3 text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 bg-white">
                            {teamInvitations.map((inv) => {
                              const sentDate = new Date(inv.created_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                              });
                              const expiresDate = new Date(inv.expires_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                              });
                              const isPending = inv.status === 'pending';

                              return (
                                <tr key={inv.id} className="hover:bg-gray-50/70 transition-colors">
                                  <td className="px-4 py-3">
                                    <div className="font-medium text-gray-900">{inv.invitee_email}</div>
                                    {inv.invitee_name && (
                                      <div className="text-[11px] text-gray-400">@{inv.invitee_name}</div>
                                    )}
                                  </td>
                                  <td className="px-3 py-3 uppercase font-medium text-[11px] text-gray-700">
                                    {inv.role}
                                  </td>
                                  <td className="px-3 py-3">{getStatusBadge(inv.status)}</td>
                                  <td className="px-3 py-3 text-gray-500">{sentDate}</td>
                                  <td className="px-3 py-3 text-gray-500">{expiresDate}</td>
                                  <td className="px-4 py-3 text-right">
                                    {isPending ? (
                                      <button
                                        type="button"
                                        onClick={() => setInvitationToCancel(inv)}
                                        className="text-rose-600 hover:text-rose-800 hover:bg-rose-50 px-2 py-1 rounded transition-colors font-medium"
                                        title="Cancel invitation"
                                      >
                                        Cancel
                                      </button>
                                    ) : (
                                      <span className="text-gray-400 text-[11px]">—</span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </CardBody>
                </Card>
              )}

            </div>
            
            {/* Right Column (Invite Form & Members) */}
            <div className="space-y-6">
              
              {/* Invite Member Card */}
              {isOwnerOrAdmin && (
                <Card className="bg-white border-gray-200">
                  <CardHeader>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                      <Mail size={18} className="mr-2 text-blue-600" />
                      Invite Member
                    </h2>
                  </CardHeader>
                  <CardBody>
                    <form onSubmit={handleInvite} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">
                          Email Address
                        </label>
                        <Input
                          placeholder="colleague@example.com"
                          type="email"
                          required
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">
                          Assigned Role
                        </label>
                        <select
                          value={inviteRole}
                          onChange={(e: any) => setInviteRole(e.target.value)}
                          className="w-full px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="member">Member</option>
                          <option value="admin">Admin</option>
                        </select>
                      </div>

                      <Button type="submit" className="w-full" variant="primary" disabled={isInviting}>
                        {isInviting ? 'Sending...' : 'Send Invitation'}
                      </Button>
                    </form>
                  </CardBody>
                </Card>
              )}

              {/* Members List Card */}
              <Card className="bg-white border-gray-200">
                <CardHeader>
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                    <Users size={18} className="mr-2 text-blue-600" />
                    Team Members ({members.length})
                  </h2>
                </CardHeader>
                <CardBody className="p-0">
                  <ul className="divide-y divide-gray-100">
                    {members.map(m => (
                      <li key={m.id} className="p-4 flex items-center justify-between hover:bg-gray-50/50 transition-colors">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs uppercase">
                            {(m.user?.username || m.user_id)?.[0]}
                          </div>
                          <div>
                            <div className="font-medium text-gray-900 text-sm">
                              {m.user?.username || m.user_id}
                              {m.user?.id === user?.id && (
                                <span className="ml-1.5 text-[11px] text-blue-600 font-semibold bg-blue-50 px-1.5 py-0.2 rounded">
                                  (You)
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-gray-500 uppercase mt-0.5">
                              <ShieldCheck size={12} className="text-gray-400" />
                              {m.role}
                            </div>
                          </div>
                        </div>
                        {isOwnerOrAdmin && m.user?.id !== user?.id && (
                          <button 
                            onClick={() => setMemberToRemove(m)}
                            className="text-gray-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                            title="Remove member"
                          >
                            <UserMinus size={16} />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </CardBody>
              </Card>
            </div>
          </div>
        </div>
      </div>

      {/* Remove Member Modal */}
      <Modal 
        isOpen={!!memberToRemove} 
        onClose={() => setMemberToRemove(null)}
        title="Remove Member?"
      >
        <p className="text-gray-600 mb-6 text-sm">
          Are you sure you want to remove <span className="font-semibold text-gray-900">{memberToRemove?.user?.username}</span> from the team? They will immediately lose access to all team conversations.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={() => setMemberToRemove(null)}>Cancel</Button>
          <Button variant="danger" onClick={confirmRemoveMember}>Remove Member</Button>
        </div>
      </Modal>

      {/* Cancel Invitation Modal */}
      <Modal
        isOpen={!!invitationToCancel}
        onClose={() => setInvitationToCancel(null)}
        title="Cancel Team Invitation?"
      >
        <p className="text-gray-600 mb-6 text-sm">
          Are you sure you want to cancel the invitation sent to{' '}
          <span className="font-semibold text-gray-900">{invitationToCancel?.invitee_email}</span>?
          The recipient will no longer be able to accept it.
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" disabled={isCancelling} onClick={() => setInvitationToCancel(null)}>
            Keep Invitation
          </Button>
          <Button variant="danger" disabled={isCancelling} onClick={confirmCancelInvitation}>
            {isCancelling ? 'Cancelling...' : 'Cancel Invitation'}
          </Button>
        </div>
      </Modal>

    </AppLayout>
  );
}
