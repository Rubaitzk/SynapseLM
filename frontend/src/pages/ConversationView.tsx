import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';

export default function ConversationView() {
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [content, setContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [participants, setParticipants] = useState<any[]>([]);
  const [teamMembers, setTeamMembers] = useState<any[]>([]);
  const [selectedUser, setSelectedUser] = useState('');

  const fetchConversation = async () => {
    try {
      const res = await api.get(`/conversations/${id}`);
      setConversation(res.data);
      
      // Fetch team members to know who we can add
      const membersRes = await api.get(`/teams/${res.data.team_id}/members`);
      setTeamMembers(membersRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchParticipants = async () => {
    try {
      const res = await api.get(`/conversations/${id}/participants`);
      setParticipants(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchMessages = async () => {
    try {
      const res = await api.get(`/conversations/${id}/messages?page=1&size=50`);
      setMessages(res.data.items);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchConversation();
    fetchParticipants();
    fetchMessages();
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      await api.post(`/conversations/${id}/messages`, { content });
      setContent('');
      fetchMessages();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddParticipant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      await api.post(`/conversations/${id}/participants/${selectedUser}`);
      setSelectedUser('');
      fetchParticipants();
    } catch (err) {
      console.error(err);
      alert('Failed to add participant. You may need higher privileges or they are already added.');
    }
  };

  if (!conversation) return <div className="p-8">Loading...</div>;

  // Filter out users who are already participants
  const availableMembers = teamMembers.filter(
    tm => !participants.some(p => p.user_id === tm.user_id)
  );

  return (
    <div className="flex h-screen max-w-6xl mx-auto bg-gray-50 dark:bg-gray-900 border-x dark:border-gray-700">
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="p-4 bg-white dark:bg-gray-800 shadow z-10 flex items-center gap-4">
          <Link to={`/teams/${conversation.team_id}`} className="text-blue-600 hover:underline">
            &larr; Back to Team
          </Link>
          <h2 className="text-xl font-bold">{conversation.title}</h2>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && <p className="text-center text-gray-500 my-8">No messages yet.</p>}
          {messages.map(msg => (
            <div key={msg.id} className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border dark:border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-sm">{msg.sender_type === 'user' ? (msg.sender?.username || 'User') : 'System/AI'}</span>
                <span className="text-xs text-gray-500">{new Date(msg.created_at).toLocaleTimeString()}</span>
              </div>
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 border-t dark:border-gray-700">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              className="flex-1 px-4 py-2 border rounded-full dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Type your message..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
            <button type="submit" className="px-6 py-2 bg-blue-600 text-white font-semibold rounded-full hover:bg-blue-700">
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Sidebar for Participants */}
      <div className="w-64 bg-white dark:bg-gray-800 border-l dark:border-gray-700 p-4 flex flex-col">
        <h3 className="font-bold text-lg mb-4">Participants</h3>
        
        <div className="flex-1 overflow-y-auto mb-4 space-y-2">
          {participants.map(p => (
            <div key={p.id} className="text-sm p-2 bg-gray-100 dark:bg-gray-700 rounded">
              {p.user?.username || p.user_id}
            </div>
          ))}
        </div>

        <div className="pt-4 border-t dark:border-gray-700">
          <h4 className="font-semibold text-sm mb-2">Add Member</h4>
          <form onSubmit={handleAddParticipant} className="flex flex-col gap-2">
            <select 
              className="px-2 py-1 border rounded text-sm dark:bg-gray-700 dark:border-gray-600"
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
            >
              <option value="">Select...</option>
              {availableMembers.map(m => (
                <option key={m.user_id} value={m.user_id}>{m.user?.username || m.user_id}</option>
              ))}
            </select>
            <button 
              type="submit" 
              disabled={!selectedUser}
              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
            >
              Add to Chat
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
