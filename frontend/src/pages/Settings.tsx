import { useState, useEffect } from 'react';
import api from '../lib/api';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { useToast } from '../context/ToastContext';
import { 
  Key, 
  CheckCircle2, 
  AlertCircle, 
  Trash2, 
  Eye, 
  EyeOff, 
  ExternalLink, 
  ShieldCheck, 
  Loader2 
} from 'lucide-react';

interface CredentialResponse {
  id: string;
  provider_name: string;
  is_configured: boolean;
  created_at?: string;
  updated_at?: string;
}

const PROVIDER_METADATA: Record<string, {
  label: string;
  description: string;
  docsUrl: string;
  docsLabel: string;
  placeholder: string;
}> = {
  gemini: {
    label: "Google Gemini",
    description: "Required for Gemini models (e.g., gemini-3.6-flash, gemini-3.8-flash).",
    docsUrl: "https://aistudio.google.com/app/apikey",
    docsLabel: "Get a Gemini API Key (Google AI Studio)",
    placeholder: "AIzaSy..."
  },
  openai: {
    label: "OpenAI",
    description: "Required for OpenAI models (e.g., gpt-4o, gpt-4-turbo, gpt-3.5-turbo).",
    docsUrl: "https://platform.openai.com/api-keys",
    docsLabel: "Get an OpenAI API Key (OpenAI Platform)",
    placeholder: "sk-proj-..."
  }
};

export default function Settings() {
  const { addToast } = useToast();
  const [credentials, setCredentials] = useState<CredentialResponse[]>([]);
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [showMask, setShowMask] = useState<Record<string, boolean>>({});
  const [savingProvider, setSavingProvider] = useState<string | null>(null);
  const [deleteConfirmProvider, setDeleteConfirmProvider] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const res = await api.get('/credentials/');
      setCredentials(res.data);
    } catch (err: any) {
      if (err.response?.status !== 401) {
        addToast(err.response?.data?.detail || "Failed to load credentials.", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (provider: string) => {
    const rawKey = keyInputs[provider]?.trim();
    if (!rawKey) return;

    setSavingProvider(provider);
    try {
      await api.post('/credentials/', {
        provider_name: provider,
        api_key: rawKey
      });

      addToast(`${PROVIDER_METADATA[provider]?.label || provider} credential verified and saved securely.`, 'success');
      // Clear key from memory immediately after save
      setKeyInputs(prev => ({ ...prev, [provider]: '' }));
      fetchCredentials();
    } catch (err: any) {
      const detail = err.response?.data?.detail || "Validation or save failed. Please verify your API key.";
      addToast(detail, 'error');
    } finally {
      setSavingProvider(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteConfirmProvider) return;

    setDeleting(true);
    try {
      await api.delete(`/credentials/${deleteConfirmProvider}`);
      addToast(`${PROVIDER_METADATA[deleteConfirmProvider]?.label || deleteConfirmProvider} credential deleted.`, 'success');
      setDeleteConfirmProvider(null);
      fetchCredentials();
    } catch (err: any) {
      addToast(err.response?.data?.detail || "Failed to delete credential.", 'error');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AppLayout>
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-4xl mx-auto space-y-8">
          
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
            <p className="text-gray-500 mt-1">Manage your AI provider credentials and personal configuration.</p>
          </div>

          {/* Security Notice Card */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-5 flex items-start gap-3">
            <ShieldCheck className="text-blue-600 w-6 h-6 shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900 space-y-1">
              <p className="font-semibold text-blue-950">Secure Per-User Credentials</p>
              <p className="text-blue-800">
                Your API keys are encrypted at rest using AES-Fernet cryptography and are decrypted only in memory when executing requests. 
                In team or shared chats, your messages always use your personal key. Saved keys are never displayed or returned in API responses.
              </p>
            </div>
          </div>

          {/* Provider Credentials List */}
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm divide-y divide-gray-100">
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Key className="w-5 h-5 text-gray-700" />
                LLM Provider API Keys
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Configure credentials for models you want to use. Keys are validated directly with the provider before being stored.
              </p>
            </div>

            {loading ? (
              <div className="p-12 flex justify-center items-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              </div>
            ) : (
              <div className="p-6 space-y-8">
                {credentials.map(c => {
                  const meta = PROVIDER_METADATA[c.provider_name] || {
                    label: c.provider_name.toUpperCase(),
                    description: `API key for ${c.provider_name}.`,
                    docsUrl: "#",
                    docsLabel: "Provider Documentation",
                    placeholder: "Enter API key"
                  };
                  const isConfigured = c.is_configured;
                  const inputValue = keyInputs[c.provider_name] || '';
                  const isVisible = showMask[c.provider_name] || false;
                  const isSaving = savingProvider === c.provider_name;

                  return (
                    <div key={c.provider_name} className="border border-gray-200 rounded-lg p-5 space-y-4 bg-gray-50/50">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2.5">
                            <span className="font-semibold text-gray-900 text-base">{meta.label}</span>
                            {isConfigured ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium bg-green-100 text-green-800 px-2.5 py-0.5 rounded-full border border-green-200">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Configured
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full border border-amber-200">
                                <AlertCircle className="w-3.5 h-3.5" /> Not Configured
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-600 mt-1">{meta.description}</p>
                        </div>

                        {meta.docsUrl !== "#" && (
                          <a
                            href={meta.docsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors"
                          >
                            {meta.docsLabel}
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>

                      {/* Input & Action buttons */}
                      <div className="space-y-2">
                        <label className="block text-xs font-medium text-gray-700">
                          {isConfigured ? "Replace API Key" : "Add API Key"}
                        </label>
                        <div className="flex flex-col sm:flex-row gap-2.5">
                          <div className="relative flex-1">
                            <input
                              type={isVisible ? "text" : "password"}
                              placeholder={meta.placeholder}
                              autoComplete="off"
                              spellCheck="false"
                              value={inputValue}
                              onChange={e => setKeyInputs(prev => ({ ...prev, [c.provider_name]: e.target.value }))}
                              className="w-full border border-gray-300 rounded-lg px-3.5 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                            />
                            {inputValue && (
                              <button
                                type="button"
                                onClick={() => setShowMask(prev => ({ ...prev, [c.provider_name]: !isVisible }))}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                title={isVisible ? "Hide key" : "Show key"}
                              >
                                {isVisible ? <EyeOff size={16} /> : <Eye size={16} />}
                              </button>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <Button
                              onClick={() => handleSave(c.provider_name)}
                              disabled={!inputValue || isSaving}
                              className="whitespace-nowrap"
                            >
                              {isSaving ? (
                                <>
                                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                  Verifying...
                                </>
                              ) : isConfigured ? (
                                "Update Key"
                              ) : (
                                "Save Key"
                              )}
                            </Button>

                            {isConfigured && (
                              <Button
                                variant="secondary"
                                onClick={() => setDeleteConfirmProvider(c.provider_name)}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50 border-gray-200"
                                title="Delete saved credential"
                              >
                                <Trash2 size={16} />
                              </Button>
                            )}
                          </div>
                        </div>

                        <p className="text-[11px] text-gray-400">
                          {isConfigured
                            ? "Your key is active. Enter a new key above if you need to rotate or replace it."
                            : "Enter your personal key above. It will be verified against the provider API before saving."}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteConfirmProvider}
        onClose={() => setDeleteConfirmProvider(null)}
        title="Delete API Credential?"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Are you sure you want to remove your saved <span className="font-semibold text-gray-900">{PROVIDER_METADATA[deleteConfirmProvider || '']?.label || deleteConfirmProvider}</span> credential?
          </p>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
            After deletion, requests using this provider will fall back to system defaults if configured, or fail with a configuration error until a new key is provided.
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setDeleteConfirmProvider(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
              {deleting ? 'Deleting...' : 'Delete Credential'}
            </Button>
          </div>
        </div>
      </Modal>
    </AppLayout>
  );
}

