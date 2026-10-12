import React, { useState, useEffect } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { AlertCircle, CheckCircle, ArrowLeft, Lock, Eye, EyeOff } from 'lucide-react';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isVerifying, setIsVerifying] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setTokenError('No password reset token provided. Please use the link sent to your email.');
      setIsVerifying(false);
      return;
    }

    const verifyToken = async () => {
      try {
        await api.post('/auth/verify-reset-token', { token });
        setTokenError(null);
      } catch (err: any) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          setTokenError(detail);
        } else {
          setTokenError('This password reset link is invalid or has expired.');
        }
      } finally {
        setIsVerifying(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (newPassword.length < 8) {
      setFormError('Password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setFormError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: newPassword,
      });
      setSuccess(true);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setFormError(detail);
      } else {
        setFormError('Failed to reset password. Please try again or request a new link.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isVerifying) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-sm border border-gray-200 text-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-sm text-gray-600">Verifying your reset link...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-blue-600 mb-2">SynapseLM</h1>
          <h2 className="text-xl font-semibold text-gray-900">Set new password</h2>
          <p className="text-sm text-gray-500 mt-1">
            Choose a strong password to secure your account.
          </p>
        </div>

        {tokenError && (
          <div className="space-y-4">
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-left">
              <div className="flex items-center text-red-800 font-semibold mb-1">
                <AlertCircle size={18} className="mr-2 text-red-600" />
                Invalid or Expired Link
              </div>
              <p className="text-sm text-red-700 leading-relaxed">
                {tokenError}
              </p>
            </div>
            <div className="space-y-2 pt-2">
              <Link to="/forgot-password">
                <Button className="w-full flex items-center justify-center">
                  Request a new reset link
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="secondary" className="w-full flex items-center justify-center">
                  <ArrowLeft size={16} className="mr-2" />
                  Return to sign in
                </Button>
              </Link>
            </div>
          </div>
        )}

        {!tokenError && success && (
          <div className="space-y-5">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-left">
              <div className="flex items-center text-green-800 font-semibold mb-1">
                <CheckCircle size={18} className="mr-2 text-green-600" />
                Password Reset Successfully
              </div>
              <p className="text-sm text-green-700 leading-relaxed">
                Your password has been securely updated. Any prior sessions have been revoked. You can now sign in with your new password.
              </p>
            </div>
            <div className="pt-2">
              <Button onClick={() => navigate('/login')} className="w-full flex items-center justify-center">
                Sign in to your account
              </Button>
            </div>
          </div>
        )}

        {!tokenError && !success && (
          <>
            {formError && (
              <div className="flex items-start p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded">
                <AlertCircle size={16} className="mr-2 flex-shrink-0 mt-0.5 text-red-600" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <Input
                  label="New Password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="At least 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={isSubmitting}
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-8 text-gray-400 hover:text-gray-600 text-xs"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              <Input
                label="Confirm New Password"
                type={showPassword ? 'text' : 'password'}
                required
                placeholder="Re-enter your new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSubmitting}
              />

              <div className="text-xs text-gray-500 space-y-1 bg-gray-50 p-2.5 rounded border border-gray-100">
                <p className="font-medium text-gray-700">Security requirement:</p>
                <p className={newPassword.length >= 8 ? 'text-green-600 font-medium' : 'text-gray-500'}>
                  • Minimum 8 characters
                </p>
                <p className={newPassword && confirmPassword && newPassword === confirmPassword ? 'text-green-600 font-medium' : 'text-gray-500'}>
                  • Passwords must match
                </p>
              </div>

              <Button type="submit" className="w-full flex items-center justify-center" disabled={isSubmitting}>
                <Lock size={16} className="mr-2" />
                {isSubmitting ? 'Updating password...' : 'Reset Password'}
              </Button>
            </form>

            <div className="text-center pt-2">
              <Link to="/login" className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 font-medium">
                <ArrowLeft size={14} className="mr-1.5" />
                Back to sign in
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
