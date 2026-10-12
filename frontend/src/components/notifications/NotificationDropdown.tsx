import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Check, X, Users, MailOpen, ArrowRight } from 'lucide-react';
import { useNotifications } from '../../context/NotificationContext';

interface NotificationDropdownProps {
  className?: string;
}

export function NotificationDropdown({ className = '' }: NotificationDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const {
    unreadCount,
    pendingInvitations,
    loading,
    acceptInvitation,
    declineInvitation,
  } = useNotifications();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleAccept = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (actionLoadingId) return;
    setActionLoadingId(id);
    try {
      await acceptInvitation(id);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDecline = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (actionLoadingId) return;
    setActionLoadingId(id);
    try {
      await declineInvitation(id);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleViewAll = () => {
    setIsOpen(false);
    navigate('/invitations');
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
        title="Team Invitations & Notifications"
        aria-label="Team Invitations & Notifications"
      >
        <Bell size={20} className={unreadCount > 0 ? 'text-blue-600' : 'text-gray-600'} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[11px] font-bold text-white bg-red-500 rounded-full ring-2 ring-white animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden transform transition-all animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-gray-900 text-sm">Notifications</span>
              {unreadCount > 0 ? (
                <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {unreadCount} pending
                </span>
              ) : (
                <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">
                  All caught up
                </span>
              )}
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-gray-600 p-1 rounded-md"
              title="Close"
            >
              <X size={16} />
            </button>
          </div>

          {/* Notification List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-gray-100">
            {loading && pendingInvitations.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-500">
                <div className="inline-block w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-2"></div>
                <p>Loading invitations...</p>
              </div>
            ) : pendingInvitations.length === 0 ? (
              <div className="p-8 text-center">
                <MailOpen size={36} className="mx-auto text-gray-300 mb-2" />
                <p className="text-sm font-medium text-gray-700">No pending invitations</p>
                <p className="text-xs text-gray-500 mt-1">
                  Team invitations from other members will show up here.
                </p>
              </div>
            ) : (
              pendingInvitations.map((inv) => (
                <div
                  key={inv.id}
                  className="p-4 hover:bg-gray-50/80 transition-colors flex flex-col gap-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">
                        <Users size={16} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900 leading-snug">
                          {inv.team?.name || 'Team Invitation'}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Invited by{' '}
                          <span className="font-medium text-gray-700">
                            {inv.inviter?.username || inv.inviter?.email || 'Team Admin'}
                          </span>
                        </p>
                      </div>
                    </div>
                    <span className="uppercase text-[10px] font-bold px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                      {inv.role}
                    </span>
                  </div>

                  {/* Quick Action Buttons */}
                  <div className="flex items-center gap-2 mt-1 pl-10">
                    <button
                      type="button"
                      disabled={actionLoadingId === inv.id}
                      onClick={(e) => handleAccept(e, inv.id)}
                      className="flex-1 inline-flex items-center justify-center px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
                    >
                      <Check size={14} className="mr-1" />
                      {actionLoadingId === inv.id ? 'Accepting...' : 'Accept'}
                    </button>
                    <button
                      type="button"
                      disabled={actionLoadingId === inv.id}
                      onClick={(e) => handleDecline(e, inv.id)}
                      className="flex-1 inline-flex items-center justify-center px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                    >
                      <X size={14} className="mr-1" />
                      {actionLoadingId === inv.id ? 'Declining...' : 'Decline'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
            <button
              onClick={handleViewAll}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center transition-colors w-full justify-center py-1"
            >
              Open Invitations Inbox <ArrowRight size={13} className="ml-1" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
