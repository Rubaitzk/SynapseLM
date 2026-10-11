import re

filepath = r'D:\Hackathons\SynapseLM\frontend\src\components\layout\AppLayout.tsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add state
content = content.replace(
    'const [teamsExpanded, setTeamsExpanded] = useState(() => localStorage.getItem(\'sidebar_teams_expanded\') !== \'false\');',
    '''const [teamsExpanded, setTeamsExpanded] = useState(() => localStorage.getItem('sidebar_teams_expanded') !== 'false');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true');

  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed));
  }, [sidebarCollapsed]);'''
)

# Update imports
content = content.replace(
    'MessageSquare, Users, LogOut, Menu, ChevronDown, ChevronRight, Settings, Plus, Search',
    'MessageSquare, Users, LogOut, Menu, ChevronDown, ChevronRight, Settings, Plus, Search, PanelLeft'
)

# Replace width
content = content.replace(
    '<div className={`${mobileMenuOpen ? \'flex\' : \'hidden\'} md:flex flex-col w-64 bg-gray-50 border-r border-gray-200 h-full absolute md:relative z-10 shrink-0`}>',
    '<div className={`${mobileMenuOpen ? \'flex\' : \'hidden\'} md:flex flex-col ${sidebarCollapsed ? \'w-16\' : \'w-64\'} transition-all duration-200 bg-gray-50 border-r border-gray-200 h-full absolute md:relative z-10 shrink-0 overflow-hidden`}>'
)

# Update logo area
content = content.replace(
    '''<div className="p-4 hidden md:block">
          <h1 className="text-xl font-bold text-gray-900">SynapseLM</h1>
        </div>''',
    '''<div className="p-4 hidden md:flex items-center justify-between">
          {!sidebarCollapsed && <h1 className="text-xl font-bold text-gray-900 truncate">SynapseLM</h1>}
          <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)} className="text-gray-500 hover:text-gray-900 ml-auto">
            <PanelLeft size={20} />
          </button>
        </div>'''
)

# Update New Chat button
content = content.replace(
    '''<span className="flex items-center">
              <Plus size={18} className="mr-2" />
              New Chat
            </span>''',
    '''<span className="flex items-center justify-center w-full">
              <Plus size={18} className={sidebarCollapsed ? "" : "mr-2"} />
              {!sidebarCollapsed && "New Chat"}
            </span>'''
)
content = content.replace(
    'className="flex items-center justify-between w-full px-4 py-2.5 text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 shadow-sm transition-colors"',
    'className={`flex items-center justify-between w-full py-2.5 text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 shadow-sm transition-colors ${sidebarCollapsed ? "px-2" : "px-4"}`}'
)

# Update Chats and Teams sections
content = content.replace(
    '''{chatsExpanded && (''',
    '''{!sidebarCollapsed && chatsExpanded && ('''
)
content = content.replace(
    '''{teamsExpanded && (''',
    '''{!sidebarCollapsed && teamsExpanded && ('''
)

# Update section headers (Chats)
content = content.replace(
    '''<button 
                onClick={() => setChatsExpanded(!chatsExpanded)}
                className="flex items-center flex-1 text-xs font-semibold text-gray-500 hover:text-gray-900 uppercase tracking-wider"
              >
                {chatsExpanded ? <ChevronDown size={14} className="mr-1" /> : <ChevronRight size={14} className="mr-1" />}
                Chats
              </button>
              <button onClick={() => navigate('/chats')} className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-gray-900 p-1" title="View all chats">
                <Search size={14} />
              </button>''',
    '''{sidebarCollapsed ? (
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
              )}'''
)

# Update section headers (Teams)
content = content.replace(
    '''<button 
                onClick={() => setTeamsExpanded(!teamsExpanded)}
                className="flex items-center flex-1 text-xs font-semibold text-gray-500 hover:text-gray-900 uppercase tracking-wider"
              >
                {teamsExpanded ? <ChevronDown size={14} className="mr-1" /> : <ChevronRight size={14} className="mr-1" />}
                Teams
              </button>
              <button onClick={() => navigate('/teams')} className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-gray-900 p-1" title="View all teams">
                <Search size={14} />
              </button>''',
    '''{sidebarCollapsed ? (
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
              )}'''
)

# Update Footer
content = content.replace(
    '''<div className="flex items-center min-w-0">
              <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center text-blue-700 font-bold mr-2 shrink-0">
                {user?.username?.[0]?.toUpperCase()}
              </div>
              <span className="truncate">{user?.username}</span>
            </div>
            <Settings size={16} className="text-gray-400 group-hover:text-gray-600 shrink-0" />''',
    '''<div className="flex items-center min-w-0 justify-center w-full">
              <div className={`w-6 h-6 rounded bg-blue-100 flex items-center justify-center text-blue-700 font-bold shrink-0 ${sidebarCollapsed ? "" : "mr-2"}`}>
                {user?.username?.[0]?.toUpperCase()}
              </div>
              {!sidebarCollapsed && <span className="truncate mr-2">{user?.username}</span>}
            </div>
            {!sidebarCollapsed && <Settings size={16} className="text-gray-400 group-hover:text-gray-600 shrink-0" />}'''
)

content = content.replace(
    '''<LogOut size={16} className="mr-2 text-gray-400" />
            Log out''',
    '''<LogOut size={16} className={sidebarCollapsed ? "text-gray-400 mx-auto" : "mr-2 text-gray-400"} />
            {!sidebarCollapsed && "Log out"}'''
)
content = content.replace(
    '''<button 
            onClick={logout}
            className="flex items-center w-full p-2 text-sm text-gray-700 rounded-md hover:bg-gray-200 transition-colors mt-1"
          >''',
    '''<button 
            onClick={logout}
            className={`flex items-center w-full p-2 text-sm text-gray-700 rounded-md hover:bg-gray-200 transition-colors mt-1 ${sidebarCollapsed ? "justify-center" : ""}`}
            title="Log out"
          >'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
