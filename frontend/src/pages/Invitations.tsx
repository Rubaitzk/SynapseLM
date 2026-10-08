import { useState, useEffect } from 'react';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { Card, CardBody } from '../components/ui/Card';
import { useToast } from '../context/ToastContext';
import { MailOpen, Check, X } from 'lucide-react';

export default function Invitations() {
  const [invitations, setInvitations] = useState<any[]>([]);
  const { addToast } = useToast();

  const fetchInvitations = async () => {
    try {
      const response = await api.get('/invitations/');
      setInvitations(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, []);

  const handleAction = async (id: string, action: 'accept' | 'reject') => {
    try {
      await api.post(`/invitations/${id}/${action}`);
      addToast(`Invitation ${action}ed`, 'success');
      fetchInvitations();
    } catch (err: any) {
      addToast(err.response?.data?.detail || `Failed to ${action} invitation`, 'error');
    }
  };

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Pending Invitations</h1>
          </div>
          
          <div className="space-y-4">
            {invitations.length === 0 ? (
              <div className="text-center py-16 bg-white border border-dashed border-gray-300 rounded-lg">
                <MailOpen size={48} className="mx-auto text-gray-300 mb-4" />
                <h3 className="text-lg font-medium text-gray-900">No pending invitations</h3>
                <p className="text-gray-500 mt-1">When someone invites you to a team, it will appear here.</p>
              </div>
            ) : (
              invitations.map(inv => (
                <Card key={inv.id}>
                  <CardBody className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                      <p className="font-semibold text-gray-900 text-lg">Team Invitation</p>
                      <p className="text-sm text-gray-500 mt-1">
                        You've been invited to join team ID: <span className="font-medium text-gray-700">{inv.team_id}</span> as a <span className="uppercase text-xs font-semibold bg-gray-100 px-1.5 py-0.5 rounded">{inv.role}</span>
                      </p>
                    </div>
                    <div className="flex gap-2 w-full sm:w-auto">
                      <Button 
                        variant="secondary" 
                        className="flex-1 sm:flex-none text-red-600 hover:text-red-700 hover:bg-red-50 border-gray-200"
                        onClick={() => handleAction(inv.id, 'reject')}
                      >
                        <X size={16} className="mr-1" /> Decline
                      </Button>
                      <Button 
                        className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700"
                        onClick={() => handleAction(inv.id, 'accept')}
                      >
                        <Check size={16} className="mr-1" /> Accept
                      </Button>
                    </div>
                  </CardBody>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
