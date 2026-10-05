import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';

export default function ConversationView() {
  const { id } = useParams<{ id: string }>();
  const [conversation, setConversation] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [content, setContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchConversation = async () => {
    try {
      const res = await api.get(`/conversations/${id}`);
      setConversation(res.data);
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
      fetchMessages(); // Refresh messages (polling style for now)
    } catch (err) {
      console.error(err);
    }
  };

  if (!conversation) return <div className="p-8">Loading...</div>;

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto bg-gray-50 dark:bg-gray-900 border-x dark:border-gray-700">
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
              <span className="font-semibold text-sm">{msg.sender_type === 'user' ? 'User' : 'System/AI'}</span>
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
  );
}
