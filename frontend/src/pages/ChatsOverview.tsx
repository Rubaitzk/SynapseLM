import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { MessageSquare, Search } from 'lucide-react';

export default function ChatsOverview() {
  const [chats, setChats] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const res = await api.get('/conversations/');
        setChats(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchChats();
  }, []);

  const filteredChats = chats.filter(c => 
    (c.title || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Chats</h1>
            <div className="relative w-full md:w-64">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search size={16} className="text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search conversations..."
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <div className="text-gray-500">Loading chats...</div>
          ) : filteredChats.length > 0 ? (
            <div className="space-y-4">
              {filteredChats.map(chat => (
                <Link 
                  key={chat.id} 
                  to={`/conversations/${chat.id}`}
                  className="block bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                        {chat.title || 'Untitled Conversation'}
                      </h3>
                      <div className="flex items-center text-sm text-gray-500 mt-2 space-x-3">
                        <span className="flex items-center">
                          <MessageSquare size={14} className="mr-1.5" />
                          Chat
                        </span>
                        <span>•</span>
                        <span>{new Date(chat.updated_at || chat.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-16 border border-dashed border-gray-300 rounded-2xl">
              <MessageSquare size={40} className="mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No chats found</h3>
              <p className="text-gray-500 mt-1">Start a new conversation to see it here.</p>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
