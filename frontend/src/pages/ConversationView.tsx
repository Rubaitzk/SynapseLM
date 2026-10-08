import React, { useState, useEffect, useRef } from 'react';

import { useParams, useNavigate } from 'react-router-dom';

import api from '../lib/api';

import { AppLayout } from '../components/layout/AppLayout';

import { Input } from '../components/ui/Input';

import { Button } from '../components/ui/Button';

import { Modal } from '../components/ui/Modal';

import { useToast } from '../context/ToastContext';

import { Trash2, Send, Users, PanelRight, AlertCircle, Cpu, MessageSquare } from 'lucide-react';



export default function ConversationView() {

  const { id } = useParams<{ id: string }>();

  const navigate = useNavigate();

  const { addToast } = useToast();

  

  const [conversation, setConversation] = useState<any>(null);

  const [participants, setParticipants] = useState<any[]>([]);

  const [teamMembers, setTeamMembers] = useState<any[]>([]);

  const [messages, setMessages] = useState<any[]>([]);

  const [content, setContent] = useState('');

  

  const [showConfig, setShowConfig] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [aiConfig, setAiConfig] = useState<any>({});

  

  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'offline'>('connecting');

  const ws = useRef<WebSocket | null>(null);

  const [activeUsers, setActiveUsers] = useState<Record<string, boolean>>({});

  const [typingUsers, setTypingUsers] = useState<Record<string, string>>({});

  const [streamingMessages, setStreamingMessages] = useState<Record<string, { content: string, failed?: boolean }>>({});

  

  const [selectedUser, setSelectedUser] = useState('');

  

  // Modals

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const [memberToRemove, setMemberToRemove] = useState<string | null>(null);



  const messagesEndRef = useRef<HTMLDivElement>(null);

  const typingTimeoutRef = useRef<any>(null);

  const isTypingRef = useRef(false);



  // Stop accepting events flag

  const isRevokedRef = useRef(false);



  const fetchConversation = async () => {

    try {

      const res = await api.get(`/conversations/${id}`);

      setConversation(res.data);

      setAiConfig({

        ai_provider: res.data.ai_provider || 'gemini',

        ai_model: res.data.ai_model || 'gemini-1.5-flash',

        ai_execution_target: res.data.ai_execution_target || 'hosted',

        ai_temperature: res.data.ai_temperature ?? 0.7,

        ai_system_instructions: res.data.ai_system_instructions || ''

      });

      

      if (res.data.team_id) {
        const membersRes = await api.get(`/teams/${res.data.team_id}/members`);
        setTeamMembers(membersRes.data);
      } else {
        setTeamMembers([]);
      }

    } catch (err: any) {

      if (err.response?.status === 403 || err.response?.status === 404) {

        addToast("Conversation unavailable. It may have been deleted or you no longer have access.", "error");

        navigate('/');

      }

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

      if (isRevokedRef.current) return;

      

      // Determine base URL dynamically or fallback to localhost:8000

      const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

      // If vite proxies /api, it might proxy /ws as well, but standard is direct

      const wsUrl = `${wsProtocol}//${host}/ws/${id}?token=${token}`;

      

      try {

        ws.current = new WebSocket(wsUrl);

      } catch (e) {

        console.error("WS connect failed", e);

        return;

      }

      

      ws.current.onopen = () => {

        setConnectionStatus('connected');

      };



      ws.current.onmessage = (event) => {

        if (isRevokedRef.current) return;

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

               let next = exists ? prev.map(m => m.id === data.message.id ? data.message : m) : [...prev, data.message];

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

               if (next[data.message_id]) next[data.message_id].failed = true;

               return next;

             });

          } else if (data.event === 'conversation.deleted') {

             isRevokedRef.current = true;

             if (ws.current) ws.current.close();

             addToast('Conversation deleted by another member.', 'error');

             navigate('/');

          } else if (data.event === 'participant.removed') {

             const tokenPayload = localStorage.getItem('token')!.split('.')[1];

             const currentUserId = JSON.parse(atob(tokenPayload)).sub;

             if (data.user_id === currentUserId) {

                 isRevokedRef.current = true;

                 if (ws.current) ws.current.close();

                 addToast('You have been removed from this conversation.', 'error');

                 navigate('/');

             } else {

                 fetchParticipants();

             }

          }

        } catch (e) {

          console.error("Failed to parse ws message", e);

        }

      };

      

      ws.current.onclose = () => {

        if (isRevokedRef.current) return;

        setConnectionStatus('reconnecting');

        reconnectTimer = setTimeout(() => {

           fetchPresence();

           fetchMessages();

           connectWs();

        }, 3000);

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

  }, [id, navigate, addToast]);



  useEffect(() => {

    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  }, [messages, streamingMessages]);



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

    if (isRevokedRef.current) return;

    

    const payload = content;

    setContent('');

    stopTyping();

    

    try {

      const res = await api.post(`/conversations/${id}/messages`, { content: payload });

      setMessages(prev => {

         const exists = prev.find(m => m.id === res.data.id);

         let next = exists ? prev.map(m => m.id === res.data.id ? res.data : m) : [...prev, res.data];

         return next.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

      });

    } catch (err: any) {

      addToast(err.response?.data?.detail || "Failed to send message", "error");

      setContent(payload); // restore content

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

      addToast('Participant added', 'success');

    } catch (err: any) {

      addToast(err.response?.data?.detail || 'Failed to add participant', 'error');

    }

  };



  const confirmRemoveParticipant = async () => {

    if (!memberToRemove) return;

    try {

      await api.delete(`/conversations/${id}/participants/${memberToRemove}`);

      setMemberToRemove(null);

      fetchParticipants();

      addToast('Participant removed', 'success');

    } catch (err: any) {

      addToast(err.response?.data?.detail || 'Failed to remove participant', 'error');

      setMemberToRemove(null);

    }

  };



  const confirmDeleteConv = async () => {

    try {

      await api.delete(`/conversations/${id}`);

      addToast('Conversation deleted', 'success');

      navigate('/');

    } catch (err: any) {

      addToast(err.response?.data?.detail || 'Failed to delete conversation', 'error');

      setDeleteModalOpen(false);

    }

  };



  const handleSaveConfig = async () => {

    try {

      await api.patch(`/conversations/${id}`, aiConfig);

      setShowConfig(false);

      addToast('AI Configuration saved', 'success');

      fetchConversation();

    } catch (err: any) {

      addToast(err.response?.data?.detail || 'Failed to save config', 'error');

    }

  };



  if (!conversation) {

    return (

      <AppLayout>

        <div className="flex-1 flex items-center justify-center">

          <div className="text-gray-500">Loading conversation...</div>

        </div>

      </AppLayout>

    );

  }



  const typingArray = Object.values(typingUsers);

  const typingText = typingArray.length > 0 

    ? `${typingArray.join(', ')} ${typingArray.length === 1 ? 'is' : 'are'} typing...`

    : '';



  const availableMembers = teamMembers.filter(m => !participants.find(p => p.user_id === m.user_id));



  return (

    <AppLayout>

      <div className="flex-1 flex overflow-hidden">

        

        {/* Main Chat Area */}

        <div className="flex-1 flex flex-col bg-gray-50 min-w-0">

          

          {/* Header */}

          <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">

            <div>

              <h2 className="text-xl font-bold text-gray-900 truncate">{conversation.title || 'Untitled'}</h2>

              <div className="flex items-center text-xs text-gray-500 mt-1 space-x-3">

                <span className="flex items-center">

                  <span className={`w-2 h-2 rounded-full mr-1.5 ${

                    connectionStatus === 'connected' ? 'bg-green-500' :

                    connectionStatus === 'connecting' || connectionStatus === 'reconnecting' ? 'bg-amber-500' : 'bg-red-500'

                  }`}></span>

                  {connectionStatus === 'connected' ? 'Connected' :

                   connectionStatus === 'connecting' ? 'Connecting...' :

                   connectionStatus === 'reconnecting' ? 'Reconnecting...' : 'Offline'}

                </span>

                <span>•</span>

                <span>{participants.length} participants</span>

              </div>

            </div>

            

            <div className="flex items-center gap-2">
              {/* V2 Extension Point: Action Menu (Share, Rename, Add to Team, Archive) */}
              <Button variant="secondary" size="sm" onClick={() => setShowConfig(true)}>
                <Cpu size={16} className="mr-2" />
                AI: {conversation.ai_provider}
              </Button>
              <button 
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                title="Toggle sidebar"
              >
                <PanelRight size={20} />
              </button>
            </div>

          </div>



          {/* Messages */}

          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">

            {messages.length === 0 && Object.keys(streamingMessages).length === 0 && (

              <div className="flex flex-col items-center justify-center h-full text-gray-500">

                <MessageSquare size={48} className="mb-4 text-gray-300" />

                <p>No messages yet. Start the conversation!</p>

              </div>

            )}

            

            {messages.map(msg => (

              <div key={msg.id} className={`flex flex-col ${msg.sender_type === 'user' ? 'items-end' : 'items-start'}`}>

                <div className="flex items-baseline mb-1 mx-1">

                  <span className="text-sm font-medium text-gray-700 mr-2">

                    {msg.sender_type === 'user' ? (msg.sender?.username || 'User') : 'SynapseLM'}

                  </span>

                  <span className="text-xs text-gray-400">

                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}

                  </span>

                </div>

                <div className={`max-w-[85%] rounded-2xl px-5 py-3 shadow-sm ${

                  msg.sender_type === 'user' 

                    ? 'bg-blue-600 text-white rounded-tr-sm' 

                    : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'

                }`}>

                  <div className="whitespace-pre-wrap">{msg.content}</div>

                </div>

              </div>

            ))}

            

            {/* Streaming */}

            {Object.entries(streamingMessages).map(([msgId, msg]) => (

               <div key={msgId} className="flex flex-col items-start">

                 <div className="flex items-baseline mb-1 mx-1">

                   <span className="text-sm font-medium text-gray-700 mr-2">SynapseLM</span>

                   <span className="text-xs text-blue-500 animate-pulse">Generating...</span>

                 </div>

                 <div className="max-w-[85%] rounded-2xl px-5 py-3 shadow-sm bg-white border border-blue-200 text-gray-800 rounded-tl-sm">

                   <div className="whitespace-pre-wrap">{msg.content}</div>

                   {msg.failed && <div className="text-red-500 text-sm mt-2 flex items-center"><AlertCircle size={14} className="mr-1"/> Failed to generate response.</div>}

                 </div>

               </div>

            ))}

            <div ref={messagesEndRef} />

          </div>



          {/* Composer */}

          <div className="bg-white border-t border-gray-200 p-4 shrink-0">

            <div className="max-w-4xl mx-auto">

              <div className="text-xs text-gray-500 italic h-5 mb-1 px-2">

                {typingText}

              </div>

              <form onSubmit={handleSend} className="flex gap-2">

                <input

                  type="text"

                  className="flex-1 px-4 py-3 bg-gray-50 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors"

                  placeholder="Type your message..."

                  value={content}

                  onChange={(e) => handleInput(e.target.value)}

                  disabled={connectionStatus !== 'connected'}

                />

                <Button 

                  type="submit" 

                  className="rounded-full px-6" 

                  disabled={!content.trim() || connectionStatus !== 'connected'}

                >

                  <Send size={18} />

                </Button>

              </form>

            </div>

          </div>

        </div>



        {/* Right Sidebar - Participants */}

        {sidebarOpen && (
        <div className="hidden lg:flex w-72 flex-col bg-white border-l border-gray-200 shrink-0">

          <div className="p-4 border-b border-gray-200">

            <h3 className="font-semibold text-gray-900 flex items-center">

              <Users size={18} className="mr-2" />

              Participants

            </h3>

          </div>

          

          <div className="flex-1 overflow-y-auto p-4 space-y-3">

            {participants.map(p => (

              <div key={p.id} className="flex items-center justify-between group">

                <div className="flex items-center min-w-0">

                  <div className="relative mr-3">

                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm shrink-0">

                      {(p.user?.username || p.user_id)[0].toUpperCase()}

                    </div>

                    {activeUsers[p.user_id] && (

                      <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full"></span>

                    )}

                  </div>

                  <span className="text-sm font-medium text-gray-900 truncate">

                    {p.user?.username || p.user_id}

                  </span>

                </div>

                <button 

                  onClick={() => setMemberToRemove(p.user_id)}

                  className="text-xs text-red-500 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-700 font-medium"

                >

                  Remove

                </button>

              </div>

            ))}

          </div>



          <div className="p-4 border-t border-gray-200 space-y-6">

            {conversation.team_id && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-3">Add Member</h4>
                <form onSubmit={handleAddParticipant} className="space-y-2">
                  <select 
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={selectedUser}
                    onChange={(e) => setSelectedUser(e.target.value)}
                  >
                    <option value="">Select a team member...</option>
                    {availableMembers.map(m => (
                      <option key={m.user_id} value={m.user_id}>{m.user?.username || m.user_id}</option>
                    ))}
                  </select>
                  <Button type="submit" variant="secondary" className="w-full text-sm" disabled={!selectedUser}>
                    Add to Chat
                  </Button>
                </form>
              </div>
            )}

            

            <div className="pt-4 border-t border-gray-100">

               <Button 

                  variant="danger" 

                  className="w-full text-sm" 

                  onClick={() => setDeleteModalOpen(true)}

               >

                  <Trash2 size={16} className="mr-2" />

                  Delete Chat

               </Button>

            </div>

          </div>

        </div>
        )}
      </div>



      {/* Modals */}

      <Modal isOpen={showConfig} onClose={() => setShowConfig(false)} title="AI Configuration">

        <div className="space-y-4">

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>

            <select 

              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"

              value={aiConfig.ai_provider}

              onChange={e => setAiConfig({...aiConfig, ai_provider: e.target.value})}

            >

              <option value="gemini">Gemini</option>

              <option value="openai">OpenAI</option>

              <option value="mock">Mock</option>

            </select>

          </div>

          <Input 

            label="Model"

            value={aiConfig.ai_model}

            onChange={e => setAiConfig({...aiConfig, ai_model: e.target.value})}

          />

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-1">Execution Target</label>

            <select 

              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"

              value={aiConfig.ai_execution_target}

              onChange={e => setAiConfig({...aiConfig, ai_execution_target: e.target.value})}

            >

              <option value="hosted">Hosted (Cloud)</option>

              <option value="local_runtime">Local Runtime</option>

              <option value="team_runtime">Team Runtime</option>

            </select>

          </div>

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-1">Temperature ({aiConfig.ai_temperature})</label>

            <input 

              type="range" min="0" max="2" step="0.1"

              className="w-full"

              value={aiConfig.ai_temperature}

              onChange={e => setAiConfig({...aiConfig, ai_temperature: parseFloat(e.target.value)})}

            />

          </div>

          <div>

            <label className="block text-sm font-medium text-gray-700 mb-1">System Instructions</label>

            <textarea 

              className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 h-24 text-sm resize-none"

              placeholder="Optional instructions for the AI"

              value={aiConfig.ai_system_instructions}

              onChange={e => setAiConfig({...aiConfig, ai_system_instructions: e.target.value})}

            />

          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">

            <Button variant="ghost" onClick={() => setShowConfig(false)}>Cancel</Button>

            <Button onClick={handleSaveConfig}>Save Configuration</Button>

          </div>

        </div>

      </Modal>



      <Modal isOpen={deleteModalOpen} onClose={() => setDeleteModalOpen(false)} title="Delete Conversation?">

        <p className="text-gray-600 mb-6">

          This will permanently delete this conversation and all its messages. This action cannot be undone.

        </p>

        <div className="flex justify-end gap-3">

          <Button variant="ghost" onClick={() => setDeleteModalOpen(false)}>Cancel</Button>

          <Button variant="danger" onClick={confirmDeleteConv}>Delete Conversation</Button>

        </div>

      </Modal>



      <Modal isOpen={!!memberToRemove} onClose={() => setMemberToRemove(null)} title="Remove Participant?">

        <p className="text-gray-600 mb-6">

          Are you sure you want to remove this participant? They will immediately lose access to the conversation.

        </p>

        <div className="flex justify-end gap-3">

          <Button variant="ghost" onClick={() => setMemberToRemove(null)}>Cancel</Button>

          <Button variant="danger" onClick={confirmRemoveParticipant}>Remove</Button>

        </div>

      </Modal>



    </AppLayout>

  );

}

