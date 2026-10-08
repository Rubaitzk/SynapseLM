import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { MessageSquare, Users, LogOut, Menu, ChevronDown, ChevronRight, Settings, Plus, Search, PanelLeft } from 'lucide-react';
import api from '../../lib/api';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [chatsExpanded, setChatsExpanded] = useState(() => localStorage.getItem('sidebar_chats_expanded') !== 'false');
  const [teamsExpanded, setTeamsExpanded] = useState(() => localStorage.getItem('sidebar_teams_expanded') !== 'false');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true');

  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  const [recentChats, setRecentChats] = useState<any[]>([]);
  const [recentTeams, setRecentTeams] = useState<any[]>([]);

  useEffect(() => {
    localStorage.setItem('sidebar_chats_expanded', String(chatsExpanded));
  }, [chatsExpanded]);

  useEffect(() => {
    localStorage.setItem('sidebar_teams_expanded', String(teamsExpanded));
  }, [teamsExpanded]);

  useEffect(() => {
    const fetchSidebarData = async () => {
      try {
        const [chatsRes, teamsRes] = await Promise.all([
          api.get('/conversations/').catch(() => ({ data: [] })),
          api.get('/teams/').catch(() => ({ data: [] }))
        ]);
        setRecentChats(chatsRes.data.slice(0, 5));
        setRecentTeams(teamsRes.data.slice(0, 5));
      } catch (e) {}
    };
    fetchSidebarData();
  }, [location.pathname]);

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      {/* Mobile Header */}
      <div className="md:hidden absolute top-0 left-0 right-0 z-20 flex items-center justify-between bg-white border-b border-gray-200 px-4 py-3">
        <h1 className="text-xl font-bold text-gray-900">SynapseLM</h1>
        <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="text-gray-600">
          <Menu size={24} />
        </button>
      </div>

      {/* Sidebar */}
      <div className={`${mobileMenuOpen ? 'flex' : 'hidden'} md:flex flex-col ${sidebarCollapsed ? 'w-16' : 'w-64'} transition-all duration-200 bg-gray-50 border-r border-gray-200 h-full absolute md:relative z-10 shrink-0 overflow-hidden`}>
        <div className="p-4 hidden md:flex items-center justify-between">
          {!sidebarCollapsed && <h1 className="text-xl font-bold text-gray-900 truncate">SynapseLM</h1>}
          <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)} className="text-gray-500 hover:text-gray-900 ml-auto">
            <PanelLeft size={20} />
          </button>
        </div>
        
        <div className="px-3 py-2 mt-12 md:mt-0">
          <button
            onClick={() => {
              navigate('/');
              setMobileMenuOpen(false);
            }}
            className={`flex items-center justify-between w-full py-2.5 text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 shadow-sm transition-colors ${sidebarCollapsed ? "px-2" : "px-4"}`}
          >
            <span className="flex items-center justify-center w-full">
              <Plus size={18} className={sidebarCollapsed ? "" : "mr-2"} />
              {!sidebarCollapsed && "New Chat"}
            </span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4 mt-2">
          
          {/* Chats Section */}
          <div>
            <div className="flex items-center justify-between group px-2 py-1">
              {sidebarCollapsed ? (
                <button onClick={() => navigate('/chats')} className="mx-auto text-gray-500 hover:text-gray-900 p-1" title="Chats">
                  <MessageSquare size={18} />
                </button>
              ) : (
                <>
                  <button 
                    onClick={() => setChatsExpanded(!chatsExpanded)}
                    className="flex items-center flex-1 text-xs font-semibold text-gray-500 hover:text-gray-900 uppercase tracking-wider"
                  >
                    {chatsExpanded ? <ChevronDown size={14} className="mr-1" /> : <ChevronRight size={14} className="mr-1" />}
                    Chats
                  </button>
                  <button onClick={() => navigate('/chats')} className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-gray-900 p-1" title="View all chats">
                    <Search size={14} />
                  </button>
                </>
              )}
            </div>
            
            {!sidebarCollapsed && chatsExpanded && (
              <div className="mt-1 space-y-0.5">
                {recentChats.map(chat => (
                  <Link 
                    key={chat.id} 
                    to={`/conversations/${chat.id}`}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`block px-3 py-2 rounded-md text-sm truncate ${location.pathname === `/conversations/${chat.id}` ? 'bg-gray-200 text-gray-900 font-medium' : 'text-gray-700 hover:bg-gray-200'}`}
                  >
                    {chat.title || 'Untitled'}
                  </Link>
                ))}
                {recentChats.length === 0 && <div className="px-3 py-2 text-xs text-gray-400">No recent chats</div>}
              </div>
            )}
          </div>

          {/* Teams Section */}
          <div>
            <div className="flex items-center justify-between group px-2 py-1">
              {sidebarCollapsed ? (
                <button onClick={() => navigate('/teams')} className="mx-auto text-gray-500 hover:text-gray-900 p-1" title="Teams">
                  <Users size={18} />
                </button>
              ) : (
                <>
                  <button 
                    onClick={() => setTeamsExpanded(!teamsExpanded)}
                    className="flex items-center flex-1 text-xs font-semibold text-gray-500 hover:text-gray-900 uppercase tracking-wider"
                  >
                    {teamsExpanded ? <ChevronDown size={14} className="mr-1" /> : <ChevronRight size={14} className="mr-1" />}
                    Teams
                  </button>
                  <button onClick={() => navigate('/teams')} className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-gray-900 p-1" title="View all teams">
                    <Search size={14} />
                  </button>
                </>
              )}
            </div>
            
            {!sidebarCollapsed && teamsExpanded && (
              <div className="mt-1 space-y-0.5">
                {recentTeams.map(team => (
                  <Link 
                    key={team.id} 
                    to={`/teams/${team.id}`}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`block px-3 py-2 rounded-md text-sm truncate ${location.pathname === `/teams/${team.id}` ? 'bg-gray-200 text-gray-900 font-medium' : 'text-gray-700 hover:bg-gray-200'}`}
                  >
                    {team.name}
                  </Link>
                ))}
                {recentTeams.length === 0 && <div className="px-3 py-2 text-xs text-gray-400">No teams</div>}
              </div>
            )}
          </div>

        </div>

        <div className="p-3 border-t border-gray-200">
          <div className="flex items-center justify-between w-full p-2 text-sm text-gray-700 rounded-md hover:bg-gray-200 transition-colors group cursor-pointer" onClick={() => navigate('/settings')}>
            <div className="flex items-center min-w-0 justify-center w-full">
              <div className={`w-6 h-6 rounded bg-blue-100 flex items-center justify-center text-blue-700 font-bold shrink-0 ${sidebarCollapsed ? "" : "mr-2"}`}>
                {user?.username?.[0]?.toUpperCase()}
              </div>
              {!sidebarCollapsed && <span className="truncate mr-2">{user?.username}</span>}
            </div>
            {!sidebarCollapsed && <Settings size={16} className="text-gray-400 group-hover:text-gray-600 shrink-0" />}
          </div>
          <button 
            onClick={logout}
            className={`flex items-center w-full p-2 text-sm text-gray-700 rounded-md hover:bg-gray-200 transition-colors mt-1 ${sidebarCollapsed ? "justify-center" : ""}`}
            title="Log out"
          >
            <LogOut size={16} className={sidebarCollapsed ? "text-gray-400 mx-auto" : "mr-2 text-gray-400"} />
            {!sidebarCollapsed && "Log out"}
          </button>
        </div>
      </div>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-0 bg-black/20" onClick={() => setMobileMenuOpen(false)}></div>
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative pt-14 md:pt-0">
        {children}
      </main>
    </div>
  );
}
