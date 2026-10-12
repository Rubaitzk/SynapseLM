import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { AlertCircle, CheckCircle, ArrowLeft, Mail } from 'lucide-react';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const emailTrimmed = email.trim();
    if (!emailTrimmed) {
      setError('Please enter your email address.');
      return;
    }

    setIsLoading(true);
    try {
      await api.post('/auth/forgot-password', { email: emailTrimmed });
      setSubmitted(true);
    } catch (err: any) {
      if (err.response?.status === 429) {
        setError(err.response?.data?.detail || 'Too many password reset requests. Please wait a few minutes and try again.');
      } else if (err.response?.data?.detail) {
        setError(typeof err.response.data.detail === 'string' ? err.response.data.detail : 'Failed to request password reset.');
      } else {
        setError('Network error: Unable to contact the server. Please check your connection.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-blue-600 mb-2">SynapseLM</h1>
          <h2 className="text-xl font-semibold text-gray-900">Reset your password</h2>
          <p className="text-sm text-gray-500 mt-1">
            Enter your email address and we'll send you a link to reset your password.
          </p>
        </div>

        {error && (
          <div className="flex items-start p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded">
            <AlertCircle size={16} className="mr-2 flex-shrink-0 mt-0.5 text-red-600" />
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          <div className="space-y-5">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-left">
              <div className="flex items-center text-green-800 font-semibold mb-1">
                <CheckCircle size={18} className="mr-2 text-green-600" />
                Check your inbox
              </div>
              <p className="text-sm text-green-700 leading-relaxed">
                If an account exists with <span className="font-medium text-green-900">{email}</span>, a secure password reset link has been dispatched. The link will remain active for 30 minutes.
              </p>
            </div>
            <p className="text-xs text-gray-500 text-center">
              Didn't receive an email? Check your spam folder or contact your workspace administrator for manual account recovery.
            </p>
            <div className="pt-2">
              <Link to="/login">
                <Button variant="secondary" className="w-full flex items-center justify-center">
                  <ArrowLeft size={16} className="mr-2" />
                  Return to sign in
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Email Address"
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />

            <Button type="submit" className="w-full flex items-center justify-center" disabled={isLoading}>
              <Mail size={16} className="mr-2" />
              {isLoading ? 'Sending instructions...' : 'Send reset link'}
            </Button>

            <div className="text-center pt-2">
              <Link to="/login" className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 font-medium">
                <ArrowLeft size={14} className="mr-1.5" />
                Back to sign in
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
