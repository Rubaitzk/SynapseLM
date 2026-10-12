import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import api from '../lib/api';
import { useAuth } from './AuthContext';
import { useToast } from './ToastContext';

export interface TeamInvitation {
  id: string;
  team_id: string;
  inviter_id: string;
  invitee_email: string;
  role: string;
  status: 'pending' | 'accepted' | 'rejected' | 'cancelled' | 'expired';
  expires_at: string;
  created_at: string;
  team?: {
    id: string;
    name: string;
  };
  inviter?: {
    id: string;
    username: string;
    email: string;
  };
  invitee_name?: string | null;
}

interface NotificationContextType {
  unreadCount: number;
  pendingInvitations: TeamInvitation[];
  loading: boolean;
  refreshNotifications: () => Promise<void>;
  acceptInvitation: (id: string) => Promise<void>;
  declineInvitation: (id: string) => Promise<void>;
  subscribeToEvents: (listener: (event: any) => void) => () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, token } = useAuth();
  const { addToast } = useToast();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [pendingInvitations, setPendingInvitations] = useState<TeamInvitation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const pingIntervalRef = useRef<any>(null);
  const eventListenersRef = useRef<Set<(event: any) => void>>(new Set());

  const subscribeToEvents = useCallback((listener: (event: any) => void) => {
    eventListenersRef.current.add(listener);
    return () => {
      eventListenersRef.current.delete(listener);
    };
  }, []);

  const refreshNotifications = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const [countRes, pendingRes] = await Promise.all([
        api.get('/invitations/unread-count'),
        api.get('/invitations/?status=pending')
      ]);
      setUnreadCount(countRes.data?.count ?? 0);
      setPendingInvitations(pendingRes.data || []);
    } catch (err) {
      console.error('Failed to load notifications', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const acceptInvitation = async (id: string) => {
    try {
      await api.post(`/invitations/${id}/accept`);
      addToast('Team invitation accepted! You are now a member.', 'success');
      await refreshNotifications();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to accept invitation';
      addToast(msg, 'error');
      throw err;
    }
  };

  const declineInvitation = async (id: string) => {
    try {
      await api.post(`/invitations/${id}/decline`);
      addToast('Team invitation declined', 'info');
      await refreshNotifications();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to decline invitation';
      addToast(msg, 'error');
      throw err;
    }
  };

  // Initial load when user logs in
  useEffect(() => {
    if (user && token) {
      refreshNotifications();
    } else {
      setUnreadCount(0);
      setPendingInvitations([]);
    }
  }, [user, token, refreshNotifications]);

  // Realtime WebSocket Connection
  useEffect(() => {
    if (!user || !token) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    let isUnmounted = false;
    let reconnectDelay = 1000;

    const getWsUrl = (authToken: string) => {
      const envWsUrl = import.meta.env.VITE_WS_BASE_URL;
      if (envWsUrl) {
        return `${envWsUrl.replace(/\/$/, '')}/ws/notifications?token=${authToken}`;
      }
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (apiBase && (apiBase.startsWith('http://') || apiBase.startsWith('https://'))) {
        try {
          const parsed = new URL(apiBase);
          const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
          return `${protocol}//${parsed.host}/ws/notifications?token=${authToken}`;
        } catch {
          // fallback
        }
      }
      const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${host}/ws/notifications?token=${authToken}`;
    };

    const connectWs = () => {
      if (isUnmounted || !token) return;

      try {
        const url = getWsUrl(token);
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          reconnectDelay = 1000;
          // Setup heartbeat ping
          if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping' }));
            }
          }, 25000);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'pong') return;

            // Notify active subscribers (e.g., TeamDetails dashboard)
            eventListenersRef.current.forEach((cb) => {
              try {
                cb(data);
              } catch (e) {
                console.error('Error in event subscriber', e);
              }
            });

            // Handle specific invitation notification events
            if (data.event === 'team.invitation.created') {
              // If directed to current user
              if (data.team_name) {
                addToast(
                  `New Team Invitation: You've been invited to join "${data.team_name}"${data.inviter_name ? ` by ${data.inviter_name}` : ''}!`,
                  'info'
                );
              }
              refreshNotifications();
            } else if (data.event === 'team.invitation.cancelled') {
              if (data.team_name) {
                addToast(`An invitation to join "${data.team_name}" was cancelled.`, 'info');
              }
              refreshNotifications();
            } else if (data.event === 'team.invitation.accepted' || data.event === 'team.invitation.declined') {
              refreshNotifications();
            }
          } catch (err) {
            console.error('Failed to parse websocket message', err);
          }
        };

        ws.onclose = () => {
          if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
          if (!isUnmounted && token) {
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
              connectWs();
            }, reconnectDelay);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        console.error('Failed to initialize notification websocket', e);
      }
    };

    connectWs();

    return () => {
      isUnmounted = true;
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [user, token, addToast, refreshNotifications]);

  return (
    <NotificationContext.Provider
      value={{
        unreadCount,
        pendingInvitations,
        loading,
        refreshNotifications,
        acceptInvitation,
        declineInvitation,
        subscribeToEvents,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
