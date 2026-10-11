import React, { useState, useEffect, useRef, useMemo } from 'react';

import { useParams, useNavigate } from 'react-router-dom';

import api from '../lib/api';

import { AppLayout } from '../components/layout/AppLayout';

import { Input } from '../components/ui/Input';

import { Button } from '../components/ui/Button';

import { Modal } from '../components/ui/Modal';

import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { Trash2, Send, Users, PanelRight, AlertCircle, Cpu, MessageSquare, Share2, Copy, Check, Clock, GitFork, CheckCircle, X } from 'lucide-react';

export default function ConversationView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const { user } = useAuth();

  const [conversation, setConversation] = useState<any>(null);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const [shareLink, setShareLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [shareExpiry, setShareExpiry] = useState<number | ''>('');
  const [activeShares, setActiveShares] = useState<any[]>([]);
  const [loadingActiveShares, setLoadingActiveShares] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const [participants, setParticipants] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [branchRequest, setBranchRequest] = useState<any>(null);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  const pendingRequests = useMemo(() => {
    return requests.filter(r => r.status === 'pending');
  }, [requests]);

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
  const [providerConfigError, setProviderConfigError] = useState<{ message: string; provider?: string } | null>(null);

  

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

        ai_model: res.data.ai_model || 'gemini-3.6-flash',

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



  
  const fetchRequests = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/conversations/${id}/requests`);
      setRequests(res.data);
    } catch (err: any) {
      if (err.response?.status !== 403) {
        console.error(err);
      }
    }
  };

  const fetchBranchRequest = async () => {
    if (!id) return;
    try {
      const res = await api.get(`/conversations/${id}/branch-request`);
      setBranchRequest(res.data);
    } catch (err: any) {
      // Ignored if not a branch or unauthenticated
    }
  };

  const fetchActiveShares = async () => {
    if (!id) return;
    setLoadingActiveShares(true);
    try {
      const res = await api.get(`/conversations/${id}/shares`);
      setActiveShares(res.data.filter((s: any) => s.is_active));
    } catch (err: any) {
      if (err.response?.status !== 403) {
        console.error("Failed to fetch active shares", err);
      }
    } finally {
      setLoadingActiveShares(false);
    }
  };

  const handleOpenShare = () => {
    setShareModalOpen(true);
    setShareLink('');
    setCopied(false);
    fetchActiveShares();
  };

  const handleCreateShare = async () => {
    if (shareLoading) return;
    setShareLoading(true);
    try {
      const payload: any = {};
      if (shareExpiry && Number(shareExpiry) > 0) {
        payload.expires_in_seconds = Number(shareExpiry);
      }
      const res = await api.post(`/conversations/${id}/shares`, payload);
      const generatedUrl = `${window.location.origin}/shares/${res.data.share_token}`;
      setShareLink(generatedUrl);
      addToast("Share link created!", "success");
      fetchActiveShares();
    } catch (err: any) {
      addToast(err.response?.data?.detail || "Failed to create share link", "error");
    } finally {
      setShareLoading(false);
    }
  };

  const handleCopyLink = (linkToCopy?: string) => {
    const target = linkToCopy || shareLink;
    if (!target) return;
    navigator.clipboard.writeText(target);
    setCopied(true);
    addToast("Share link copied to clipboard!", "success");
    setTimeout(() => setCopied(false), 2500);
  };

  const handleRevokeShare = async (shareId: string) => {
    setRevokingId(shareId);
    try {
      await api.post(`/conversations/${id}/shares/${shareId}/revoke`);
      addToast("Share link revoked", "success");
      fetchActiveShares();
    } catch (err: any) {
      addToast(err.response?.data?.detail || "Failed to revoke share link", "error");
    } finally {
      setRevokingId(null);
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
    fetchRequests();
    fetchBranchRequest();
  }, [id]);



  useEffect(() => {

    let reconnectTimer: any;

    

    const connectWs = () => {

      const token = localStorage.getItem('token');

      if (!token) return;

      if (isRevokedRef.current) return;

      

      const envWsUrl = import.meta.env.VITE_WS_BASE_URL;
      let wsUrl = '';
      if (envWsUrl) {
        wsUrl = `${envWsUrl.replace(/\/$/, '')}/ws/${id}?token=${token}`;
      } else {
        const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${wsProtocol}//${host}/ws/${id}?token=${token}`;
      }

      

      try {

        ws.current = new WebSocket(wsUrl);

      } catch (e) {

        console.error("WS connect failed", e);

        return;

      }

      

      ws.current.onopen = () => {
        

        setConnectionStatus('connected');

      
        fetchPresence();
        fetchMessages();
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

          } else if (data.event === 'participant.added') {
            fetchParticipants();
          } else if (data.event === 'request.created') {
            fetchRequests();
          } else if (data.event === 'request.accepted') {
            fetchRequests();
            fetchParticipants();
            if (data.requester_id === user?.id) {
              addToast(
                `Your collaboration request was approved! You are now a participant in "${data.conversation_title || 'the conversation'}".`,
                'success'
              );
              fetchConversation();
              fetchBranchRequest();
            }
          } else if (data.event === 'request.rejected') {
            fetchRequests();
            if (data.requester_id === user?.id) {
              addToast(
                `Your collaboration request for "${data.conversation_title || 'the conversation'}" was declined. You can continue chatting privately in this branch.`,
                'info'
              );
              fetchBranchRequest();
            }
          } else if (data.event === 'request.cancelled') {
            fetchRequests();
            fetchBranchRequest();
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

      

      ws.current.onclose = (event) => {
        if (event.code === 1008) {
          isRevokedRef.current = true;
          setConnectionStatus('offline');
          return;
        }
        if (isRevokedRef.current) return;
        setConnectionStatus('reconnecting');
        if (reconnectTimer) clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => {
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

  }, [id]);



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
      const data = err.response?.data;
      if (data?.error_code === "provider_configuration_missing") {
        const prov = conversation?.ai_provider || "AI";
        const msg = `${data.detail || `API key for ${prov} is not configured.`} Please configure your API key in Settings.`;
        addToast(msg, "error");
        setProviderConfigError({ message: msg, provider: prov });
      } else if (data?.error_code === "decryption_failed") {
        const prov = conversation?.ai_provider || "AI";
        const msg = `Decryption failed for your personal ${prov} credential. Please update your API key in Settings.`;
        addToast(msg, "error");
        setProviderConfigError({ message: msg, provider: prov });
      } else if (data?.error_code === "unsupported_provider" || data?.error_code === "invalid_provider_model_combo") {
        addToast(data.detail || "Unsupported provider or model combination.", "error");
      } else {
        addToast(data?.detail || "Failed to send message", "error");
      }
      setContent(payload); // restore content so user can retry
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



  
  const handleRequestAction = async (reqId: string, action: 'accept' | 'reject') => {
    if (actionLoading[reqId]) return;
    setActionLoading(prev => ({ ...prev, [reqId]: true }));
    try {
      await api.post(`/conversations/${id}/requests/${reqId}/${action}`);
      addToast(`Request ${action === 'accept' ? 'accepted' : 'rejected'} successfully`, 'success');
      await fetchRequests();
      if (action === 'accept') {
        await fetchParticipants();
      }
    } catch (err: any) {
      addToast(err.response?.data?.detail || `Failed to ${action} request`, 'error');
      await fetchRequests();
    } finally {
      setActionLoading(prev => ({ ...prev, [reqId]: false }));
    }
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
  const isOwner = Boolean(user && conversation && conversation.owner_id === user.id);
  const isBranch = Boolean(conversation?.parent_conversation_id);
  const isArchived = conversation?.lifecycle_state === 'archived';

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
                <span>{participants.length} {participants.length === 1 ? 'participant' : 'participants'}</span>
                {isBranch && (
                  <>
                    <span>•</span>
                    <span className="text-purple-600 font-medium">Branched snapshot</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isBranch && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                  <GitFork size={12} className="mr-1" />
                  Branch
                </span>
              )}

              {!isBranch && (
                <Button 
                  variant="secondary" 
                  size="sm" 
                  onClick={handleOpenShare}
                  disabled={!isOwner}
                  title={isOwner ? "Share conversation with others" : "Only the conversation owner can create share links"}
                >
                  <Share2 size={15} className={`mr-1.5 ${!isOwner ? 'opacity-40' : 'text-blue-600'}`} />
                  <span className={!isOwner ? 'opacity-50' : ''}>Share</span>
                </Button>
              )}

              <Button variant="secondary" size="sm" onClick={() => setShowConfig(true)}>
                <Cpu size={16} className="mr-2" />
                AI: {conversation.ai_provider}
              </Button>

              <button 
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="relative p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                title="Toggle sidebar"
                aria-label="Toggle sidebar"
              >
                <PanelRight size={20} />
                {pendingRequests.length > 0 && isOwner && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-amber-500 border-2 border-white rounded-full"></span>
                )}
              </button>
            </div>
          </div>

          {isBranch && isArchived && (
            <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-3 flex items-center justify-between text-xs text-emerald-900">
              <div className="flex items-center">
                <CheckCircle size={16} className="mr-2 text-emerald-600 shrink-0" />
                <span>
                  <strong>Collaboration access approved!</strong> This branch is archived as a read-only snapshot.
                </span>
              </div>
              {conversation.parent_conversation_id && (
                <Button 
                  size="sm" 
                  onClick={() => navigate(`/conversations/${conversation.parent_conversation_id}`)}
                  className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white ml-3 shrink-0"
                >
                  Open Main Conversation &rarr;
                </Button>
              )}
            </div>
          )}

          {isBranch && !isArchived && branchRequest?.status === 'pending' && (
            <div className="bg-amber-50 border-b border-amber-200 px-6 py-2.5 flex items-center text-xs text-amber-800">
              <Clock size={15} className="mr-2 text-amber-600 shrink-0" />
              <span>
                <strong>Collaboration request pending owner approval.</strong> Messages in this branch remain private until approved.
              </span>
            </div>
          )}

          {isBranch && !isArchived && branchRequest?.status === 'rejected' && (
            <div className="bg-gray-100 border-b border-gray-200 px-6 py-2.5 flex items-center text-xs text-gray-700">
              <AlertCircle size={15} className="mr-2 text-gray-500 shrink-0" />
              <span>
                <strong>Collaboration request was declined.</strong> You can continue chatting privately with AI in this branch.
              </span>
            </div>
          )}



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

              {providerConfigError && (
                <div className="mb-2 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between text-xs animate-in fade-in duration-200">
                  <div className="flex items-center gap-2 text-amber-900 pr-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>{providerConfigError.message}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button 
                      size="sm" 
                      onClick={() => navigate('/settings')}
                      className="text-xs py-1 px-3"
                    >
                      Go to Settings
                    </Button>
                    <button 
                      type="button"
                      onClick={() => setProviderConfigError(null)} 
                      className="text-amber-700 hover:text-amber-900 text-xs px-1.5 py-0.5 hover:underline"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )}

              <form onSubmit={handleSend} className="flex gap-2">
                <input
                  type="text"
                  className="flex-1 px-4 py-3 bg-gray-50 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                  placeholder={isArchived ? "This branch has been archived (read-only)." : "Type your message..."}
                  value={content}
                  onChange={(e) => handleInput(e.target.value)}
                  disabled={connectionStatus !== 'connected' || isArchived}
                />
                <Button 
                  type="submit" 
                  className="rounded-full px-6" 
                  disabled={!content.trim() || connectionStatus !== 'connected' || isArchived}
                >
                  <Send size={18} />
                </Button>
              </form>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Participants & Requests */}
        {sidebarOpen && (
        <>
          <div 
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 z-50 w-80 max-w-[85vw] flex flex-col bg-white shadow-2xl border-l border-gray-200 lg:static lg:w-72 lg:z-auto lg:shadow-none shrink-0 transition-all">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-gray-900 flex items-center text-sm">
                  <Users size={18} className="mr-2" />
                  Participants ({participants.length})
                </h3>
                {conversation.team_id && (
                  <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded font-medium">Team</span>
                )}
              </div>
              <button 
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 lg:hidden"
                title="Close sidebar"
                aria-label="Close sidebar"
              >
                <X size={18} />
              </button>
            </div>

            {pendingRequests.length > 0 && isOwner && (
            <div className="p-4 border-b border-gray-200 bg-amber-50">
              <h3 className="font-semibold text-gray-900 flex items-center mb-3 text-sm">
                <Users size={16} className="mr-2 text-amber-600" />
                Pending Requests ({pendingRequests.length})
              </h3>
              <div className="space-y-3">
                {pendingRequests.map(req => (
                  <div key={req.id} className="text-sm border border-amber-200 bg-white p-2.5 rounded shadow-sm">
                    <div className="font-medium text-gray-900 truncate mb-1">
                      {req.requester?.username || req.requester_id}
                    </div>
                    <div className="text-[11px] text-gray-500 mb-2">
                      Requested collaboration access
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        className="flex-1 py-1 h-auto text-xs" 
                        disabled={Boolean(actionLoading[req.id])}
                        onClick={() => handleRequestAction(req.id, 'accept')}
                      >
                        {actionLoading[req.id] ? 'Processing...' : 'Accept'}
                      </Button>
                      <Button 
                        size="sm" 
                        variant="ghost" 
                        className="flex-1 py-1 h-auto text-xs" 
                        disabled={Boolean(actionLoading[req.id])}
                        onClick={() => handleRequestAction(req.id, 'reject')}
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            )}

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

                  {isOwner && p.user_id !== user?.id && (
                    <button 
                      onClick={() => setMemberToRemove(p.user_id)}
                      className="text-xs text-red-500 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-700 font-medium"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-gray-200 space-y-4">
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

              {!conversation.team_id && isOwner && !isBranch && (
                <div>
                  <Button variant="secondary" className="w-full text-sm" onClick={handleOpenShare}>
                    <Share2 size={15} className="mr-2 text-blue-600" />
                    Share Conversation
                  </Button>
                </div>
              )}

              {isOwner && (
                <div className="pt-2 border-t border-gray-100">
                  <Button 
                    variant="danger" 
                    className="w-full text-sm" 
                    onClick={() => setDeleteModalOpen(true)}
                  >
                    <Trash2 size={16} className="mr-2" />
                    Delete Chat
                  </Button>
                </div>
              )}
            </div>
          </div>
        </>
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

      {/* Share Modal */}
      <Modal isOpen={shareModalOpen} onClose={() => setShareModalOpen(false)} title="Share Conversation">
        <div className="space-y-5">
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-3.5 text-xs text-blue-800 leading-relaxed">
            <p className="font-semibold mb-1 flex items-center">
              <Share2 size={14} className="mr-1.5 text-blue-600" />
              How sharing works in SynapseLM
            </p>
            <p>
              Recipients receive a read-only preview of the conversation. They can <strong>branch</strong> the conversation to continue chatting with AI in their own private copy, or <strong>request collaboration access</strong> to join this chat.
            </p>
          </div>

          <div className="space-y-3">
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Link Expiration
            </label>
            <div className="flex gap-2">
              <select 
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                value={shareExpiry}
                onChange={(e) => setShareExpiry(e.target.value ? Number(e.target.value) : '')}
                disabled={shareLoading}
              >
                <option value="">Never expires</option>
                <option value="3600">1 hour</option>
                <option value="86400">24 hours</option>
                <option value="604800">7 days</option>
                <option value="2592000">30 days</option>
              </select>

              <Button 
                onClick={handleCreateShare} 
                disabled={shareLoading}
                className="whitespace-nowrap"
              >
                {shareLoading ? 'Generating...' : 'Create Link'}
              </Button>
            </div>
          </div>

          {shareLink && (
            <div className="space-y-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <span className="block text-xs font-semibold text-gray-700">Generated Share Link</span>
              <div className="flex items-center gap-2">
                <input 
                  type="text" 
                  readOnly 
                  value={shareLink}
                  className="flex-1 px-3 py-1.5 bg-white border border-gray-300 rounded text-xs font-mono select-all focus:outline-none"
                  onClick={(e) => (e.target as HTMLInputElement).select()}
                />
                <Button 
                  size="sm" 
                  onClick={() => handleCopyLink(shareLink)}
                  className="shrink-0 flex items-center gap-1.5"
                >
                  {copied ? (
                    <>
                      <Check size={14} className="text-green-300" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>Copy</span>
                    </>
                  )}
                </Button>
              </div>
              <p className="text-[11px] text-gray-500">
                Share this link with anyone you want to give preview or branch access to.
              </p>
            </div>
          )}

          {/* Active shares list */}
          <div className="pt-3 border-t border-gray-100 space-y-2.5">
            <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider flex items-center justify-between">
              <span>Active Share Links</span>
              {loadingActiveShares && <span className="text-[11px] font-normal text-gray-400">Loading...</span>}
            </h4>

            {activeShares.length === 0 && !loadingActiveShares ? (
              <p className="text-xs text-gray-500 py-1">No active share links. Generate one above to share.</p>
            ) : (
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {activeShares.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-2.5 bg-gray-50 border border-gray-200 rounded-md text-xs">
                    <div>
                      <div className="font-medium text-gray-800 flex items-center">
                        <Clock size={12} className="mr-1 text-gray-400" />
                        {s.expires_at ? `Expires ${new Date(s.expires_at).toLocaleString()}` : 'Never expires'}
                      </div>
                      <div className="text-[11px] text-gray-400">
                        Created {new Date(s.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-red-600 hover:text-red-700 text-xs py-1 h-auto"
                      disabled={revokingId === s.id}
                      onClick={() => handleRevokeShare(s.id)}
                    >
                      {revokingId === s.id ? 'Revoking...' : 'Revoke'}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2 border-t border-gray-100">
            <Button variant="ghost" onClick={() => setShareModalOpen(false)}>Close</Button>
          </div>
        </div>
      </Modal>

    </AppLayout>

  );

}

