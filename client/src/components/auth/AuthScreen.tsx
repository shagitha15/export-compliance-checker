import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { AuthApiError } from '../../services/authService';
import tradeBg from '../../assets/trade-logistics-bg.jpg';
import {
  ShieldCheck,
  Lock,
  Mail,
  Building2,
  User,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  MailWarning,
  RefreshCw,
  ArrowLeft,
  Eye,
  EyeOff,
  Info,
} from 'lucide-react';

interface AuthScreenProps {
  initialMode?: 'login' | 'signup';
  onBackToHome?: () => void;
}

function isEmailUnconfirmedError(err: unknown): boolean {
  if (err instanceof AuthApiError && err.code === 'email_not_confirmed') {
    return true;
  }
  if (err instanceof Error && err.message.toLowerCase().includes('email not confirmed')) {
    return true;
  }
  return false;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({
  initialMode = 'login',
  onBackToHome,
}) => {
  const { login, signup, resendConfirmation, sessionNotice, clearSessionNotice } = useAuth();
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [showForgotHelp, setShowForgotHelp] = useState(false);
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [iec, setIec] = useState('');
  const [gstin, setGstin] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailNotConfirmed, setEmailNotConfirmed] = useState(false);
  const [confirmationMessage, setConfirmationMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);
  const [resendError, setResendError] = useState<string | null>(null);

  const clearFeedback = (preserveInfo = false) => {
    setError(null);
    setEmailNotConfirmed(false);
    setConfirmationMessage(null);
    setResendSuccess(null);
    setResendError(null);
    if (!preserveInfo) {
      setInfoMessage(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    clearFeedback(false);
    clearSessionNotice();

    try {
      if (mode === 'login') {
        await login(email.trim(), password, rememberMe);
      } else {
        const res = await signup({
          email: email.trim(),
          password,
          full_name: fullName || undefined,
          organization_name: orgName || undefined,
          iec: iec || undefined,
          gstin: gstin || undefined,
        });
        if (res.email_confirmation_required) {
          setInfoMessage(res.message);
          setMode('login');
        }
      }
    } catch (err: unknown) {
      if (mode === 'login' && isEmailUnconfirmedError(err)) {
        setEmailNotConfirmed(true);
        setConfirmationMessage(
          err instanceof Error
            ? err.message
            : 'Your email address has not been confirmed yet. Please check your inbox for the verification link before signing in, or resend the confirmation email.'
        );
      } else {
        setError(err instanceof Error ? err.message : 'Authentication failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendConfirmation = async () => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !trimmedEmail.includes('@')) {
      setResendSuccess(null);
      setResendError('Please enter your Email Address above to resend the confirmation link.');
      return;
    }

    setResending(true);
    setResendSuccess(null);
    setResendError(null);
    try {
      const res = await resendConfirmation(trimmedEmail);
      setResendSuccess(res.message);
    } catch (err: unknown) {
      setResendError(
        err instanceof Error ? err.message : 'Unable to resend confirmation email. Please try again.'
      );
    } finally {
      setResending(false);
    }
  };

  const handleBackToHome = () => {
    if (onBackToHome) {
      onBackToHome();
      return;
    }
    window.history.pushState({}, '', '/');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    borderRadius: '8px',
    border: '1px solid #CBD5E1',
    backgroundColor: '#FFFFFF',
    color: '#1E293B',
    boxSizing: 'border-box',
    outline: 'none',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#0B1F33',
        backgroundImage: `linear-gradient(135deg, rgba(11, 31, 51, 0.88) 0%, rgba(16, 42, 67, 0.82) 55%, rgba(13, 148, 136, 0.56) 100%), url(${tradeBg})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '28px 16px',
        fontFamily: 'var(--font-sans, "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif)',
        color: '#1E293B',
      }}
    >
      <div style={{ width: '100%', maxWidth: '460px', marginBottom: '14px' }}>
        <button
          type="button"
          id="auth-back-home-btn"
          onClick={handleBackToHome}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(11, 31, 51, 0.45)',
            border: '1px solid rgba(255, 255, 255, 0.16)',
            borderRadius: '8px',
            padding: '6px 12px',
            fontSize: '13px',
            fontWeight: 600,
            color: '#F8FAFC',
            cursor: 'pointer',
            backdropFilter: 'blur(6px)',
          }}
        >
          <ArrowLeft size={15} color="#5EEAD4" />
          <span>Back to Home</span>
        </button>
      </div>

      <div
        style={{
          width: '100%',
          maxWidth: '460px',
          backgroundColor: 'rgba(255, 255, 255, 0.97)',
          border: '1px solid rgba(226, 232, 240, 0.9)',
          borderRadius: '14px',
          boxShadow: '0 24px 54px rgba(8, 22, 38, 0.45)',
          backdropFilter: 'blur(10px)',
          overflow: 'hidden',
        }}
      >
        {/* Top Navy Header Brand */}
        <div
          style={{
            background: 'linear-gradient(135deg, #102A43 0%, #163A5C 100%)',
            color: '#FFFFFF',
            padding: '22px 26px',
            borderBottom: '3px solid #0D9488',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #0D9488 0%, #38BDF8 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: '0 4px 12px rgba(13, 148, 136, 0.35)',
              }}
            >
              <ShieldCheck size={22} color="#FFFFFF" />
            </div>
            <div>
              <div
                style={{
                  fontSize: '15px',
                  fontWeight: 800,
                  letterSpacing: '0.03em',
                  color: '#FFFFFF',
                  lineHeight: 1.2,
                }}
              >
                EXPORT CUSTOMS COMPLIANCE
              </div>
              <div style={{ fontSize: '12px', color: '#BAE6FD', marginTop: '3px' }}>
                Intelligent Document Verification &amp; Compliance Auditing
              </div>
            </div>
          </div>
        </div>

        <div style={{ padding: '24px 26px 26px' }}>
          {/* Heading + Subtitle */}
          <div style={{ marginBottom: '18px' }}>
            <h1
              style={{
                margin: 0,
                fontSize: '22px',
                fontWeight: 800,
                color: '#102A43',
                letterSpacing: '-0.015em',
              }}
            >
              {mode === 'login' ? 'Welcome Back' : 'Create Account'}
            </h1>
            <p style={{ margin: '5px 0 0', fontSize: '13.5px', color: '#475569' }}>
              {mode === 'login'
                ? 'Sign in with your Supabase-verified compliance account to access the workspace.'
                : 'Register your exporter compliance account to start auditing export documents.'}
            </p>
          </div>

          {/* Sign In / Create Account Switcher */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '6px',
              padding: '4px',
              backgroundColor: '#F1F5F9',
              borderRadius: '10px',
              marginBottom: '18px',
            }}
          >
            <button
              type="button"
              id="auth-tab-login"
              onClick={() => {
                setMode('login');
                setShowForgotHelp(false);
                clearFeedback(true);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '13px',
                fontWeight: 700,
                borderRadius: '8px',
                border: 'none',
                backgroundColor: mode === 'login' ? '#102A43' : 'transparent',
                color: mode === 'login' ? '#FFFFFF' : '#475569',
                cursor: 'pointer',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              id="auth-tab-signup"
              onClick={() => {
                setMode('signup');
                setShowForgotHelp(false);
                clearFeedback(true);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '13px',
                fontWeight: 700,
                borderRadius: '8px',
                border: 'none',
                backgroundColor: mode === 'signup' ? '#102A43' : 'transparent',
                color: mode === 'signup' ? '#FFFFFF' : '#475569',
                cursor: 'pointer',
                transition: 'background-color 0.15s ease, color 0.15s ease',
              }}
            >
              Create Account
            </button>
          </div>

          {sessionNotice && !error && !emailNotConfirmed && (
            <div
              id="auth-session-expired-banner"
              role="alert"
              style={{
                padding: '10px 12px',
                marginBottom: '14px',
                borderRadius: '8px',
                backgroundColor: '#FFFBEB',
                border: '1px solid #FDE68A',
                color: '#92400E',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertTriangle size={15} style={{ flexShrink: 0 }} />
              <span>{sessionNotice}</span>
            </div>
          )}

          {emailNotConfirmed && mode === 'login' && (
            <div
              id="auth-email-unconfirmed-banner"
              role="alert"
              style={{
                padding: '12px',
                marginBottom: '14px',
                borderRadius: '8px',
                backgroundColor: '#FFFBEB',
                border: '1px solid #FDE68A',
                color: '#92400E',
                fontSize: '12.5px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <MailWarning size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 700, marginBottom: '2px' }}>
                    Email Verification Required
                  </div>
                  <div>
                    {confirmationMessage ||
                      'Your email address has not been confirmed yet. Please confirm your email before signing in.'}
                  </div>
                </div>
              </div>
              <button
                type="button"
                id="auth-resend-confirmation-btn"
                onClick={handleResendConfirmation}
                disabled={resending}
                style={{
                  alignSelf: 'flex-start',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  borderRadius: '6px',
                  border: '1px solid #F59E0B',
                  backgroundColor: '#FFFFFF',
                  color: '#92400E',
                  cursor: resending ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {resending ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <RefreshCw size={13} />
                )}
                <span>{resending ? 'Sending confirmation...' : 'Resend confirmation email'}</span>
              </button>
            </div>
          )}

          {error && (
            <div
              id="auth-error-banner"
              role="alert"
              style={{
                padding: '10px 12px',
                marginBottom: '14px',
                borderRadius: '8px',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA',
                color: '#991B1B',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertTriangle size={15} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {resendError && (
            <div
              id="auth-resend-error-banner"
              role="alert"
              style={{
                padding: '10px 12px',
                marginBottom: '14px',
                borderRadius: '8px',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA',
                color: '#991B1B',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertTriangle size={15} style={{ flexShrink: 0 }} />
              <span>{resendError}</span>
            </div>
          )}

          {(resendSuccess || infoMessage) && (
            <div
              id={resendSuccess ? 'auth-resend-success-banner' : 'auth-info-banner'}
              role="status"
              style={{
                padding: '10px 12px',
                marginBottom: '14px',
                borderRadius: '8px',
                backgroundColor: '#F0FDF4',
                border: '1px solid #BBF7D0',
                color: '#166534',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <CheckCircle2 size={15} style={{ flexShrink: 0 }} />
              <span>{resendSuccess || infoMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {mode === 'signup' && (
              <div>
                <label
                  htmlFor="auth-fullname-input"
                  style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#1E293B', marginBottom: '5px' }}
                >
                  <User size={13} style={{ verticalAlign: 'middle', marginRight: '5px', color: '#0D9488' }} />
                  Full Name
                </label>
                <input
                  id="auth-fullname-input"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Exporter / CHA Representative"
                  style={inputStyle}
                />
              </div>
            )}

            <div>
              <label
                htmlFor="auth-email-input"
                style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#1E293B', marginBottom: '5px' }}
              >
                <Mail size={13} style={{ verticalAlign: 'middle', marginRight: '5px', color: '#0D9488' }} />
                Email Address
              </label>
              <input
                type="email"
                required
                autoComplete="email"
                id="auth-email-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="compliance@company.com"
                style={inputStyle}
              />
            </div>

            <div>
              <label
                htmlFor="auth-password-input"
                style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#1E293B', marginBottom: '5px' }}
              >
                <Lock size={13} style={{ verticalAlign: 'middle', marginRight: '5px', color: '#0D9488' }} />
                Password
              </label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={mode === 'signup' ? 8 : undefined}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  id="auth-password-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'signup' ? 'Minimum 8 characters' : 'Enter your password'}
                  style={{ ...inputStyle, paddingRight: '40px' }}
                />
                <button
                  type="button"
                  id="auth-toggle-password-btn"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((prev) => !prev)}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    background: 'none',
                    border: 'none',
                    padding: '4px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#64748B',
                    cursor: 'pointer',
                  }}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            {mode === 'login' && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  fontSize: '13px',
                }}
              >
                <label
                  htmlFor="auth-remember-me"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '7px',
                    color: '#334155',
                    cursor: 'pointer',
                    fontWeight: 500,
                    userSelect: 'none',
                  }}
                >
                  <input
                    id="auth-remember-me"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    style={{
                      width: '15px',
                      height: '15px',
                      accentColor: '#0D9488',
                      cursor: 'pointer',
                    }}
                  />
                  <span>Remember Me</span>
                </label>

                <button
                  type="button"
                  id="auth-forgot-password-btn"
                  onClick={() => setShowForgotHelp((prev) => !prev)}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    fontSize: '13px',
                    fontWeight: 600,
                    color: '#0D9488',
                    cursor: 'pointer',
                  }}
                >
                  Forgot Password?
                </button>
              </div>
            )}

            {mode === 'login' && showForgotHelp && (
              <div
                id="auth-forgot-password-panel"
                role="note"
                style={{
                  padding: '11px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#F0F9FF',
                  border: '1px solid #BAE6FD',
                  color: '#0C4A6E',
                  fontSize: '12.5px',
                  lineHeight: 1.55,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                }}
              >
                <Info size={15} style={{ flexShrink: 0, marginTop: '2px', color: '#0284C7' }} />
                <div>
                  Self-service password reset links are not enabled on this API endpoint. To reset
                  your Supabase account password, contact your workspace administrator or send a
                  recovery link from your Supabase Auth dashboard.
                </div>
              </div>
            )}

            {mode === 'signup' && (
              <div
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#102A43' }}>
                  <Building2 size={13} style={{ verticalAlign: 'middle', marginRight: '5px', color: '#0D9488' }} />
                  Organization Details (Optional)
                </div>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="Company / Exporter Organization Name"
                  style={inputStyle}
                />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <input
                    type="text"
                    value={iec}
                    onChange={(e) => setIec(e.target.value)}
                    placeholder="DGFT IEC (optional)"
                    style={inputStyle}
                  />
                  <input
                    type="text"
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value)}
                    placeholder="GSTIN (optional)"
                    style={inputStyle}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              id="auth-submit-btn"
              disabled={submitting}
              style={{
                marginTop: '4px',
                padding: '11px 16px',
                fontSize: '14px',
                fontWeight: 700,
                background: submitting
                  ? '#334E68'
                  : 'linear-gradient(135deg, #102A43 0%, #0D9488 100%)',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '8px',
                cursor: submitting ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 6px 16px rgba(16, 42, 67, 0.16)',
              }}
            >
              {submitting && <Loader2 size={16} className="animate-spin" />}
              <span>
                {mode === 'login'
                  ? submitting
                    ? 'Signing In...'
                    : 'Sign In'
                  : submitting
                    ? 'Creating Account...'
                    : 'Create Account'}
              </span>
            </button>

            {mode === 'login' && !emailNotConfirmed && (
              <div
                style={{
                  marginTop: '2px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12.5px',
                  color: '#475569',
                }}
              >
                <span>Need a verification link?</span>
                <button
                  type="button"
                  id="auth-resend-link-btn"
                  onClick={handleResendConfirmation}
                  disabled={resending}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    fontSize: '12.5px',
                    fontWeight: 600,
                    color: '#0D9488',
                    textDecoration: 'underline',
                    cursor: resending ? 'not-allowed' : 'pointer',
                  }}
                >
                  {resending ? 'Sending...' : 'Resend confirmation email'}
                </button>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};
