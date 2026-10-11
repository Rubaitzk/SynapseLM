import re

def update():
    with open("frontend/src/pages/ConversationView.tsx", "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Add requests state
    content = content.replace(
        "const [participants, setParticipants] = useState<any[]>([]);",
        "const [participants, setParticipants] = useState<any[]>([]);\n  const [requests, setRequests] = useState<any[]>([]);"
    )
    
    # 2. Add fetchRequests
    fetch_reqs = """
  const fetchRequests = async () => {
    try {
      const res = await api.get(`/conversations/${id}/requests`);
      setRequests(res.data);
    } catch (err) {
      console.error(err);
    }
  };
"""
    content = content.replace(
        "const fetchParticipants = async () => {",
        fetch_reqs + "\n  const fetchParticipants = async () => {"
    )
    
    # 3. Add fetchRequests to useEffect
    content = content.replace(
        "fetchParticipants();\n      fetchMessages();",
        "fetchParticipants();\n      fetchMessages();\n      fetchRequests();"
    )
    
    # 4. Add websocket events for requests and participants
    ws_handlers = """            } else if (data.event === 'participant.added') {
              fetchParticipants();
            } else if (data.event === 'request.created' || data.event === 'request.accepted' || data.event === 'request.rejected' || data.event === 'request.cancelled') {
              fetchRequests();
              if (data.event === 'request.accepted') fetchParticipants();
            } else if (data.event === 'message.created') {"""
    
    content = content.replace(
        "} else if (data.event === 'message.created') {",
        ws_handlers
    )
    
    # 5. Add request handlers
    handlers = """
  const handleRequestAction = async (reqId: string, action: 'accept' | 'reject') => {
    try {
      await api.post(`/conversations/${id}/requests/${reqId}/${action}`);
      addToast(`Request ${action}ed`, 'success');
      fetchRequests();
      if (action === 'accept') fetchParticipants();
    } catch (err: any) {
      addToast(err.response?.data?.detail || `Failed to ${action} request`, 'error');
    }
  };
"""
    content = content.replace(
        "const handleAddParticipant = async (e: React.FormEvent) => {",
        handlers + "\n  const handleAddParticipant = async (e: React.FormEvent) => {"
    )
    
    # 6. Add UI for requests in Sidebar
    requests_ui = """
          {requests.length > 0 && (
          <div className="p-4 border-b border-gray-200 bg-amber-50">
            <h3 className="font-semibold text-gray-900 flex items-center mb-3 text-sm">
              <Users size={16} className="mr-2 text-amber-600" />
              Pending Requests ({requests.length})
            </h3>
            <div className="space-y-3">
              {requests.map(req => (
                <div key={req.id} className="text-sm border border-amber-200 bg-white p-2 rounded">
                  <div className="font-medium truncate mb-1">{req.requester?.username || req.requester_id}</div>
                  <div className="flex gap-2">
                    <Button size="sm" className="flex-1 py-1 h-auto text-xs" onClick={() => handleRequestAction(req.id, 'accept')}>Accept</Button>
                    <Button size="sm" variant="outline" className="flex-1 py-1 h-auto text-xs" onClick={() => handleRequestAction(req.id, 'reject')}>Reject</Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          )}
"""
    content = content.replace(
        """<div className="flex-1 overflow-y-auto p-4 space-y-3">""",
        requests_ui + """\n          <div className="flex-1 overflow-y-auto p-4 space-y-3">"""
    )
    
    with open("frontend/src/pages/ConversationView.tsx", "w", encoding="utf-8") as f:
        f.write(content)
        
if __name__ == "__main__":
    update()
