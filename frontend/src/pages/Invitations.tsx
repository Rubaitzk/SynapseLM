import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { Card, CardBody } from '../components/ui/Card';
import { useToast } from '../context/ToastContext';
import { useNotifications } from '../context/NotificationContext';
import type { TeamInvitation } from '../context/NotificationContext';
import { 
  MailOpen, 
  Check, 
  X, 
  Users, 
  Clock, 
  Calendar, 
  Search, 
  ArrowRight,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';

type FilterTab = 'pending' | 'accepted' | 'declined' | 'cancelled_expired' | 'all';

export default function Invitations() {
  const [activeTab, setActiveTab] = useState<FilterTab>('pending');
  const [invitations, setInvitations] = useState<TeamInvitation[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const { addToast } = useToast();
  const { unreadCount, refreshNotifications, subscribeToEvents } = useNotifications();
  const navigate = useNavigate();

  const fetchInvitations = useCallback(async () => {
    try {
      setLoading(true);
      let queryStatus = '';
      if (activeTab === 'pending') queryStatus = 'pending';
      else if (activeTab === 'accepted') queryStatus = 'accepted';
      else if (activeTab === 'declined') queryStatus = 'rejected';
      else if (activeTab === 'cancelled_expired') queryStatus = 'all'; // filter client-side
      else queryStatus = 'all';

      const response = await api.get(`/invitations/${queryStatus ? `?status=${queryStatus}` : ''}`);
      let data: TeamInvitation[] = response.data;

      if (activeTab === 'cancelled_expired') {
        data = data.filter(i => i.status === 'cancelled' || i.status === 'expired');
      }

      setInvitations(data);
    } catch (err: any) {
      console.error('Error fetching invitations:', err);
      addToast(err.response?.data?.detail || 'Failed to load invitations', 'error');
    } finally {
      setLoading(false);
    }
  }, [activeTab, addToast]);

  useEffect(() => {
    fetchInvitations();
  }, [fetchInvitations]);

  // Subscribe to realtime updates
  useEffect(() => {
    const unsubscribe = subscribeToEvents((event) => {
      if (event.event?.startsWith('team.invitation.')) {
        fetchInvitations();
      }
    });
    return unsubscribe;
  }, [subscribeToEvents, fetchInvitations]);

  const handleAction = async (id: string, action: 'accept' | 'decline') => {
    if (actionLoadingId) return;
    setActionLoadingId(id);
    try {
      const endpoint = action === 'accept' ? `/invitations/${id}/accept` : `/invitations/${id}/decline`;
      const res = await api.post(endpoint);
      addToast(
        action === 'accept' ? 'Team invitation accepted! You are now a member.' : 'Invitation declined',
        action === 'accept' ? 'success' : 'info'
      );
      await refreshNotifications();
      await fetchInvitations();

      // If accepted, optionally allow navigating to team
      if (action === 'accept' && res.data?.team_id) {
        navigate(`/teams/${res.data.team_id}`);
      }
    } catch (err: any) {
      addToast(err.response?.data?.detail || `Failed to ${action} invitation`, 'error');
    } finally {
      setActionLoadingId(null);
    }
  };

  const filteredInvitations = invitations.filter((inv) => {
    const q = searchQuery.toLowerCase();
    const teamName = inv.team?.name?.toLowerCase() || '';
    const inviterName = inv.inviter?.username?.toLowerCase() || '';
    const inviterEmail = inv.inviter?.email?.toLowerCase() || '';
    return teamName.includes(q) || inviterName.includes(q) || inviterEmail.includes(q);
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
            <Clock size={12} className="mr-1" /> Pending
          </span>
        );
      case 'accepted':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            <Check size={12} className="mr-1" /> Accepted
          </span>
        );
      case 'rejected':
      case 'declined':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800">
            <X size={12} className="mr-1" /> Declined
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
            <AlertCircle size={12} className="mr-1" /> Cancelled
          </span>
        );
      case 'expired':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
            <Clock size={12} className="mr-1" /> Expired
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {status}
          </span>
        );
    }
  };

  const tabs: { key: FilterTab; label: string; badge?: number }[] = [
    { key: 'pending', label: 'Pending', badge: unreadCount > 0 ? unreadCount : undefined },
    { key: 'accepted', label: 'Accepted' },
    { key: 'declined', label: 'Declined' },
    { key: 'cancelled_expired', label: 'Cancelled / Expired' },
    { key: 'all', label: 'All History' },
  ];

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-gray-50/50">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Team Invitations Inbox</h1>
              <p className="text-sm text-gray-500 mt-1">
                Manage all incoming team invitations, responses, and membership invites.
              </p>
            </div>
            {/* Search */}
            <div className="relative w-full sm:w-64">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by team or inviter..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex overflow-x-auto border-b border-gray-200 gap-1 pb-px scrollbar-none">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    isActive
                      ? 'border-blue-600 text-blue-600 font-semibold'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                  {tab.badge !== undefined && tab.badge > 0 && (
                    <span className="ml-2 px-2 py-0.5 text-xs font-bold bg-blue-100 text-blue-700 rounded-full">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Invitation Cards */}
          <div className="space-y-4">
            {loading ? (
              <div className="py-20 text-center">
                <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3"></div>
                <p className="text-sm text-gray-500">Loading invitations...</p>
              </div>
            ) : filteredInvitations.length === 0 ? (
              <div className="text-center py-16 bg-white border border-dashed border-gray-300 rounded-xl p-8">
                <MailOpen size={48} className="mx-auto text-gray-300 mb-3" />
                <h3 className="text-base font-semibold text-gray-900">
                  {searchQuery ? 'No matching invitations found' : `No ${activeTab} invitations`}
                </h3>
                <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                  {activeTab === 'pending'
                    ? 'When someone invites you to join their team, your invitations will appear here.'
                    : 'Invitations matching this category will appear here.'}
                </p>
              </div>
            ) : (
              filteredInvitations.map((inv) => {
                const isPending = inv.status === 'pending';
                const isAccepted = inv.status === 'accepted';
                const createdDate = new Date(inv.created_at).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                });
                const expiresDate = new Date(inv.expires_at).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                });

                return (
                  <Card key={inv.id} className="border border-gray-200/80 hover:shadow-sm transition-all bg-white">
                    <CardBody className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-5">
                      <div className="flex items-start space-x-4">
                        <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 font-bold shrink-0">
                          <Users size={22} />
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <h3 className="text-base font-semibold text-gray-900">
                              {inv.team?.name || `Team ID: ${inv.team_id}`}
                            </h3>
                            {getStatusBadge(inv.status)}
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-700 uppercase tracking-wider">
                              <ShieldCheck size={12} className="mr-1 text-gray-500" />
                              {inv.role}
                            </span>
                          </div>

                          <p className="text-sm text-gray-600">
                            Invited by{' '}
                            <span className="font-medium text-gray-900">
                              {inv.inviter?.username || inv.inviter?.email || 'Team Admin'}
                            </span>
                            {inv.inviter?.email && inv.inviter?.username && (
                              <span className="text-gray-400 text-xs ml-1">({inv.inviter.email})</span>
                            )}
                          </p>

                          <div className="flex items-center gap-4 text-xs text-gray-500 pt-1">
                            <span className="flex items-center">
                              <Calendar size={13} className="mr-1 text-gray-400" /> Sent: {createdDate}
                            </span>
                            <span className="flex items-center">
                              <Clock size={13} className="mr-1 text-gray-400" /> Expires: {expiresDate}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 self-end md:self-center shrink-0 w-full sm:w-auto">
                        {isPending ? (
                          <>
                            <Button
                              variant="secondary"
                              disabled={actionLoadingId === inv.id}
                              className="flex-1 sm:flex-none text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-gray-200"
                              onClick={() => handleAction(inv.id, 'decline')}
                            >
                              <X size={15} className="mr-1.5" />
                              {actionLoadingId === inv.id ? 'Processing...' : 'Decline'}
                            </Button>
                            <Button
                              disabled={actionLoadingId === inv.id}
                              className="flex-1 sm:flex-none bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                              onClick={() => handleAction(inv.id, 'accept')}
                            >
                              <Check size={15} className="mr-1.5" />
                              {actionLoadingId === inv.id ? 'Accepting...' : 'Accept Invitation'}
                            </Button>
                          </>
                        ) : isAccepted ? (
                          <Button
                            variant="secondary"
                            onClick={() => navigate(`/teams/${inv.team_id}`)}
                            className="w-full sm:w-auto text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                          >
                            View Team <ArrowRight size={14} className="ml-1.5" />
                          </Button>
                        ) : null}
                      </div>
                    </CardBody>
                  </Card>
                );
              })
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
