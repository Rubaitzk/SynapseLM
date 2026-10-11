import { useState, useEffect } from 'react';
import { useToast } from '../context/ToastContext';

interface CredentialResponse {
  id: string;
  provider_name: string;
  is_configured: boolean;
}

export default function Settings() {
  const { addToast } = useToast();
  const [credentials, setCredentials] = useState<CredentialResponse[]>([]);
  const [providerInputs, setProviderInputs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8000/api/credentials/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCredentials(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (provider: string) => {
    const key = providerInputs[provider];
    if (!key) return;

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8000/api/credentials/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          provider_name: provider,
          api_key: key
        })
      });

      if (res.ok) {
        addToast(`${provider} credential saved successfully.`, 'success');
        setProviderInputs(prev => ({ ...prev, [provider]: '' }));
        fetchCredentials();
      } else {
        const data = await res.json();
        addToast(`Failed to save credential: ${data.detail || 'Unknown error'}`, 'error');
      }
    } catch (e) {
      addToast('Network error while saving credential.', 'error');
    }
  };

  const handleDelete = async (provider: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`http://localhost:8000/api/credentials/${provider}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        addToast(`${provider} credential deleted.`, 'success');
        fetchCredentials();
      } else {
        addToast('Failed to delete credential.', 'error');
      }
    } catch (e) {
      addToast('Network error while deleting credential.', 'error');
    }
  };

  if (loading) return <div className="p-8">Loading settings...</div>;

  return (
    <div className="max-w-3xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">LLM Provider Credentials</h2>
        <p className="text-gray-600 mb-6 text-sm">
          Configure your personal API keys here. They are securely encrypted and only used for your own actions.
        </p>
        
        <div className="space-y-6">
          {credentials.map(c => (
            <div key={c.provider_name} className="border p-4 rounded-md">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium capitalize">{c.provider_name}</span>
                {c.is_configured ? (
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Configured</span>
                ) : (
                  <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">Not Configured</span>
                )}
              </div>
              
              <div className="flex gap-2 mt-3">
                <input
                  type="password"
                  placeholder={`Enter ${c.provider_name} API Key`}
                  className="flex-1 border rounded px-3 py-2 text-sm"
                  value={providerInputs[c.provider_name] || ''}
                  onChange={e => setProviderInputs(prev => ({ ...prev, [c.provider_name]: e.target.value }))}
                />
                <button
                  onClick={() => handleSave(c.provider_name)}
                  className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
                  disabled={!providerInputs[c.provider_name]}
                >
                  Save
                </button>
                {c.is_configured && (
                  <button
                    onClick={() => handleDelete(c.provider_name)}
                    className="bg-red-100 text-red-600 px-4 py-2 rounded text-sm hover:bg-red-200"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
