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
  
  // Realtime state
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'offline'>('connecting');
  const ws = useRef<WebSocket | null>(null);
  const [activeUsers, setActiveUsers] = useState<Record<string, boolean>>({});
  const [typingUsers, setTypingUsers] = useState<Record<string, string>>({});
  const [streamingMessages, setStreamingMessages] = useState<Record<string, { content: string, failed?: boolean }>>({});
  
  const typingTimeoutRef = useRef<any>(null);
  const isTypingRef = useRef(false);

  const fetchConversation = async () => {
    try {
      const res = await api.get(`/conversations/${id}`);
      setConversation(res.data);
      
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

  const fetchPresence = async () => {
    try {
      const res = await api.get(`/conversations/${id}/presence`);
      const map: Record<string, boolean> = {};
      res.data.active_users.forEach((u: any) => map[u.id] = true);
      setActiveUsers(map);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchConversation();
    fetchParticipants();
    fetchMessages();
    fetchPresence();
  }, [id]);

  useEffect(() => {
    let reconnectTimer: any;
    
    const connectWs = () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      // Assume API runs on same host, port 8000
      const wsUrl = `ws://localhost:8000/ws/${id}?token=${token}`;
      ws.current = new WebSocket(wsUrl);
      
      ws.current.onopen = () => {
        setConnectionStatus('connected');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.event === 'presence.joined') {
            setActiveUsers(prev => ({...prev, [data.user_id]: true}));
          } else if (data.event === 'presence.left') {
            setActiveUsers(prev => ({...prev, [data.user_id]: false}));
          } else if (data.event === 'typing.started') {
            setTypingUsers(prev => ({...prev, [data.user_id]: data.user_name || data.user_id}));
          } else if (data.event === 'typing.stopped') {
            setTypingUsers(prev => {
              const next = {...prev};
              delete next[data.user_id];
              return next;
            });
          } else if (data.event === 'message.created') {
             setMessages(prev => {
               const exists = prev.find(m => m.id === data.message.id);
               let next;
               if (exists) {
                 next = prev.map(m => m.id === data.message.id ? data.message : m);
               } else {
                 next = [...prev, data.message];
               }
               // Sort by created_at to maintain canonical ordering
               return next.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
             });
          } else if (data.event === 'assistant.response.started') {
             setStreamingMessages(prev => ({...prev, [data.message_id]: {content: ''}}));
          } else if (data.event === 'assistant.response.delta') {
             setStreamingMessages(prev => ({
               ...prev,
               [data.message_id]: {
                 content: (prev[data.message_id]?.content || '') + data.content
               }
             }));
             messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
          } else if (data.event === 'assistant.response.completed') {
             setMessages(prev => {
               const next = [...prev, data.message];
               return next.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
             });
             setStreamingMessages(prev => {
               const next = {...prev};
               delete next[data.message_id];
               return next;
             });
          } else if (data.event === 'assistant.response.failed') {
             setStreamingMessages(prev => {
               const next = {...prev};
               if (next[data.message_id]) {
                 next[data.message_id].failed = true;
               }
               return next;
             });
          }
        } catch (e) {
          console.error("Failed to parse ws message", e);
        }
      };
      
      ws.current.onclose = () => {
        setConnectionStatus('reconnecting');
        reconnectTimer = setTimeout(() => {
           fetchPresence();
           fetchMessages();
           connectWs();
        }, 2000);
      };
    };
    
    setConnectionStatus('connecting');
    connectWs();
    
    return () => {
      clearTimeout(reconnectTimer);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const stopTyping = () => {
    isTypingRef.current = false;
    clearTimeout(typingTimeoutRef.current);
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ event: 'typing.stopped' }));
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    
    stopTyping();
    
    try {
      const res = await api.post(`/conversations/${id}/messages`, { content });
      setContent('');
      
      // Immediately display our own message via REST response
      // This guarantees the sender sees it instantly even if WS is slow
      setMessages(prev => {
         const exists = prev.find(m => m.id === res.data.id);
         let next;
         if (exists) {
           next = prev.map(m => m.id === res.data.id ? res.data : m);
         } else {
           next = [...prev, res.data];
         }
         return next.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      });
    } catch (err) {
      console.error(err);
    }
  };
  
  const handleInput = (val: string) => {
    setContent(val);
    
    if (val.trim() === '') {
      stopTyping();
      return;
    }
    
    if (!isTypingRef.current) {
      isTypingRef.current = true;
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ event: 'typing.started' }));
      }
    }
    
    clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping();
    }, 2000);
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

  const availableMembers = teamMembers.filter(
    tm => !participants.some(p => p.user_id === tm.user_id)
  );
  
  const getTypingText = () => {
    const names = Object.values(typingUsers);
    if (names.length === 0) return null;
    if (names.length === 1) return `${names[0]} is typing...`;
    if (names.length === 2) return `${names[0]} and ${names[1]} are typing...`;
    return `${names[0]}, ${names[1]}, and ${names.length - 2} others are typing...`;
  };
  
  const typingText = getTypingText();

  return (
    <div className="flex h-screen max-w-6xl mx-auto bg-gray-50 dark:bg-gray-900 border-x dark:border-gray-700">
      
      <div className="flex-1 flex flex-col min-w-0">
        <header className="p-4 bg-white dark:bg-gray-800 shadow z-10 flex items-center gap-4">
          <Link to={`/teams/${conversation.team_id}`} className="text-blue-600 hover:underline">
            &larr; Back to Team
          </Link>
          <h2 className="text-xl font-bold">{conversation.title}</h2>
          
          <div className="ml-auto text-sm flex items-center gap-2">
            {connectionStatus === 'connected' && <><span className="w-2 h-2 rounded-full bg-green-500"></span><span className="text-gray-500">Connected</span></>}
            {connectionStatus === 'reconnecting' && <><span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></span><span className="text-gray-500">Reconnecting...</span></>}
            {connectionStatus === 'connecting' && <><span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span><span className="text-gray-500">Connecting...</span></>}
          </div>
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
          
          {/* Render Streaming AI Messages */}
          {Object.entries(streamingMessages).map(([msgId, msg]) => (
             <div key={msgId} className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-blue-300 dark:border-blue-700">
               <div className="flex items-center gap-2 mb-1">
                 <span className="font-semibold text-sm">System/AI</span>
                 <span className="text-xs text-blue-500 animate-pulse">Generating...</span>
               </div>
               <div className="whitespace-pre-wrap">{msg.content}</div>
               {msg.failed && <div className="text-red-500 text-sm mt-2">Failed to generate response.</div>}
             </div>
          ))}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 border-t dark:border-gray-700 flex flex-col">
          {typingText && (
            <div className="text-xs text-gray-500 italic mb-2 h-4">{typingText}</div>
          )}
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              className="flex-1 px-4 py-2 border rounded-full dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Type your message..."
              value={content}
              onChange={(e) => handleInput(e.target.value)}
            />
            <button type="submit" className="px-6 py-2 bg-blue-600 text-white font-semibold rounded-full hover:bg-blue-700">
              Send
            </button>
          </form>
        </div>
      </div>

      <div className="w-64 bg-white dark:bg-gray-800 border-l dark:border-gray-700 p-4 flex flex-col">
        <h3 className="font-bold text-lg mb-4">Participants</h3>
        
        <div className="flex-1 overflow-y-auto mb-4 space-y-2">
          {participants.map(p => (
            <div key={p.id} className="flex items-center justify-between text-sm p-2 bg-gray-100 dark:bg-gray-700 rounded">
              <span>{p.user?.username || p.user_id}</span>
              {activeUsers[p.user_id] ? (
                <span className="w-2 h-2 rounded-full bg-green-500" title="Online"></span>
              ) : (
                <span className="w-2 h-2 rounded-full bg-gray-400" title="Offline"></span>
              )}
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
