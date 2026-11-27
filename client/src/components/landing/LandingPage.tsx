import React, { useState } from 'react';
import {
  ShieldCheck,
  Sparkles,
  GitBranch,
  Scale,
  Fingerprint,
  Landmark,
  FileCheck2,
  UploadCloud,
  ScanText,
  ArrowRight,
  Mail,
  MapPin,
  Clock,
  Menu,
  X,
  Lock,
  Database,
  Cpu,
  Globe,
  Layers,
  Code2,
} from 'lucide-react';
import './landing.css';
import officialLogoEmblem from '../../assets/official-logo-emblem.png';
import { GlobeGlitterOrbit } from './GlobeGlitterOrbit';

interface LandingPageProps {
  isAuthenticated?: boolean;
  onLoginClick: () => void;
  onGetStartedClick: () => void;
  onOpenDashboard?: () => void;
}

const FEATURES = [
  {
    icon: Sparkles,
    title: 'Gemini AI Document Extraction',
    description:
      'Schema-guided structured JSON parsing across digital and scanned PDFs with configurable timeouts, retry resilience, and non-silent PyMuPDF text fallback.',
  },
  {
    icon: GitBranch,
    title: 'LangGraph Agent Orchestration',
    description:
      'Deterministic 10-node stateful compliance workflow unifying classification, completeness checks, reconciliation, policy audit, forensics, and decision synthesis.',
  },
  {
    icon: Scale,
    title: '16-Rule Validation Engine',
    description:
      'Stage 1 intra-document arithmetic & weight checks paired with cross-document reconciliation across quantities, HS codes, currencies, values, and Incoterms.',
  },
  {
    icon: Fingerprint,
    title: 'Document Authenticity & Tamper Detection',
    description:
      'Indian GSTIN Mod-36 checksum validation, DGFT IEC & ICEGATE port checks, net-vs-gross physical laws, date chronology, and PDF metadata/font splice inspection.',
  },
  {
    icon: Landmark,
    title: 'DGFT & CBIC Policy Verification',
    description:
      'Semantic policy retrieval and compliance checks covering Foreign Trade Policy 2023, Customs Act Section 50/14, GST Rule 96A LUT, RBI FEMA, and SCOMET controls.',
  },
  {
    icon: FileCheck2,
    title: 'Automated Audit Reports',
    description:
      'Generates multi-page A4 PDF Compliance Certificates with executive scorecards, uploaded document rosters, discrepancy tables, and statutory citations.',
  },
];

const WORKFLOW_STEPS = [
  {
    step: '01',
    icon: UploadCloud,
    title: 'Upload 5 Documents',
    detail:
      'Submit Commercial Invoice, Packing List, Purchase Order, Shipping Bill, and Certificate of Origin PDFs with SHA-256 deduplication.',
  },
  {
    step: '02',
    icon: ScanText,
    title: 'AI & OCR Extraction',
    detail:
      'PyMuPDF OCR reads PDF pages while Gemini 2.5 Flash maps trade fields into strict customs JSON schemas.',
  },
  {
    step: '03',
    icon: GitBranch,
    title: 'LangGraph Orchestration',
    detail:
      'Stateful 10-node agent coordinates completeness checks and cross-document field normalization.',
  },
  {
    step: '04',
    icon: ShieldCheck,
    title: 'Policy & Fraud Audit',
    detail:
      'Verifies DGFT/CBIC/RBI mandates alongside GSTIN Mod-36 checksums, math integrity, and date ordering.',
  },
  {
    step: '05',
    icon: FileCheck2,
    title: 'PDF Audit Certificate',
    detail:
      'Outputs PASS, CONDITIONAL, or CUSTOMS HOLD decisions and downloads a complete A4 compliance report.',
  },
];

const TECHNOLOGIES = [
  { name: 'Python', role: 'Core Engines & Forensics', icon: Code2 },
  { name: 'FastAPI', role: 'Versioned REST API', icon: Globe },
  { name: 'Gemini AI', role: 'Structured Extraction & Embeddings', icon: Cpu },
  { name: 'LangGraph', role: '10-Node Agent Workflow', icon: GitBranch },
  { name: 'Supabase', role: 'PostgreSQL & JWT Auth', icon: Database },
  { name: 'Pinecone', role: 'Semantic Policy Search', icon: Layers },
];

export const LandingPage: React.FC<LandingPageProps> = ({
  isAuthenticated = false,
  onLoginClick,
  onGetStartedClick,
  onOpenDashboard,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [contactSent, setContactSent] = useState(false);
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactMessage, setContactMessage] = useState('');

  const handlePrimaryAuth = () => {
    if (isAuthenticated && onOpenDashboard) {
      onOpenDashboard();
    } else {
      onGetStartedClick();
    }
  };

  const handleNavLogin = () => {
    if (isAuthenticated && onOpenDashboard) {
      onOpenDashboard();
    } else {
      onLoginClick();
    }
  };

  const handleContactSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactName.trim() || !contactEmail.trim() || !contactMessage.trim()) return;
    setContactSent(true);
    setContactName('');
    setContactEmail('');
    setContactMessage('');
  };

  return (
    <div className="ecc-landing">
      {/* 1. Navigation Bar */}
      <header className="ecc-nav">
        <div className="ecc-nav-inner">
          <a href="#home" className="ecc-brand">
            <div className="ecc-brand-mark" aria-hidden="true">
              <ShieldCheck size={22} />
            </div>
            <div>
              <div className="ecc-brand-title">EXPORT CUSTOMS COMPLIANCE</div>
              <div className="ecc-brand-tagline">
                Intelligent Document Verification &amp; Compliance Auditing
              </div>
            </div>
          </a>

          <nav className="ecc-nav-links" aria-label="Primary Navigation">
            <a href="#home" className="ecc-nav-link ecc-nav-link-home">Home</a>
            <a href="#features" className="ecc-nav-link">Features</a>
            <a href="#how-it-works" className="ecc-nav-link">How It Works</a>
            <a href="#about-us" className="ecc-nav-link">About Us</a>
            <a href="#contact" className="ecc-nav-link">Contact</a>
          </nav>

          <div className="ecc-nav-actions">
            <button
              type="button"
              id="landing-nav-login-btn"
              onClick={handleNavLogin}
              className="ecc-btn ecc-btn-navy"
            >
              <Lock size={14} />
              <span>{isAuthenticated ? 'Open Dashboard' : 'Sign In'}</span>
            </button>
          </div>

          <button
            type="button"
            className="ecc-mobile-toggle"
            aria-label="Toggle Menu"
            onClick={() => setMobileMenuOpen((v) => !v)}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <div className={`ecc-mobile-menu ${mobileMenuOpen ? 'open' : ''}`}>
          <a href="#home" className="ecc-nav-link ecc-nav-link-home" onClick={() => setMobileMenuOpen(false)}>Home</a>
          <a href="#features" className="ecc-nav-link" onClick={() => setMobileMenuOpen(false)}>Features</a>
          <a href="#how-it-works" className="ecc-nav-link" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
          <a href="#about-us" className="ecc-nav-link" onClick={() => setMobileMenuOpen(false)}>About Us</a>
          <a href="#contact" className="ecc-nav-link" onClick={() => setMobileMenuOpen(false)}>Contact</a>
          <button
            type="button"
            onClick={() => {
              setMobileMenuOpen(false);
              handleNavLogin();
            }}
            className="ecc-btn ecc-btn-navy"
          >
            <Lock size={14} />
            <span>{isAuthenticated ? 'Open Dashboard' : 'Sign In'}</span>
          </button>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section id="home" className="ecc-hero">
        <div className="ecc-hero-glow" aria-hidden="true" />
        <div className="ecc-hero-scrim" aria-hidden="true" />

        <div className="ecc-container ecc-hero-grid">
          <div className="ecc-hero-copy">
            <div className="ecc-badge">
              <Sparkles size={14} />
              <span>Export Customs Documentation Compliance Checker</span>
            </div>
            <h1 className="ecc-hero-title">
              Smarter Export Documentation.
              <br />
              <span className="ecc-hero-accent">Faster Compliance.</span>
            </h1>
            <p className="ecc-hero-desc">
              AI-powered export document extraction, cross-document validation, tamper forensics,
              and automated DGFT &amp; CBIC policy verification for frictionless global trade.
            </p>
            <div className="ecc-hero-ctas">
              <button
                type="button"
                id="landing-hero-get-started-btn"
                onClick={handlePrimaryAuth}
                className="ecc-btn ecc-btn-primary"
                style={{ padding: '13px 26px', fontSize: '15px' }}
              >
                <span>{isAuthenticated ? 'Go to Dashboard' : 'Get Started'}</span>
                <ArrowRight size={16} />
              </button>
              <a
                href="#features"
                className="ecc-btn ecc-btn-outline"
                style={{ padding: '13px 24px', fontSize: '15px' }}
              >
                Explore Features
              </a>
            </div>

            <div className="ecc-hero-stats">
              <div>
                <div className="ecc-stat-val">5 Documents</div>
                <div className="ecc-stat-lbl">Synchronized Batch Audit</div>
              </div>
              <div>
                <div className="ecc-stat-val">10-Node Graph</div>
                <div className="ecc-stat-lbl">LangGraph Orchestration</div>
              </div>
              <div>
                <div className="ecc-stat-val">DGFT &amp; CBIC</div>
                <div className="ecc-stat-lbl">Policy + Mod-36 Forensics</div>
              </div>
            </div>
          </div>

          <div className="ecc-hero-logo-stage">
            <div className="ecc-hero-logo-aura" aria-hidden="true" />
            <div className="ecc-hero-emblem-orbit-box">
              <GlobeGlitterOrbit />
              <div className="ecc-hero-logo-wrap">
                <img
                  src={officialLogoEmblem}
                  alt="Export Customs Documentation Compliance Checker Illustration"
                  className="ecc-hero-logo-img"
                />
              </div>
            </div>
          </div>
        </div>

        <a href="#features" className="ecc-scroll-cue">
          Scroll to explore
        </a>
      </section>

      {/* 3. Features Section */}
      <section id="features" className="ecc-section ecc-section-alt">
        <div className="ecc-container">
          <div className="ecc-section-head">
            <div className="ecc-eyebrow">Platform Capabilities</div>
            <h2 className="ecc-section-title">Built for Zero-Discrepancy Customs Clearance</h2>
            <p className="ecc-section-sub">
              Every module combines structured AI extraction with deterministic rules, forensic checks, and verifiable Indian trade policy references.
            </p>
          </div>

          <div className="ecc-features-grid">
            {FEATURES.map((feat) => {
              const Icon = feat.icon;
              return (
                <article key={feat.title} className="ecc-feature-card">
                  <div className="ecc-icon-box">
                    <Icon size={22} />
                  </div>
                  <h3 className="ecc-card-title">{feat.title}</h3>
                  <p className="ecc-card-text">{feat.description}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. How It Works Section */}
      <section id="how-it-works" className="ecc-section">
        <div className="ecc-container">
          <div className="ecc-section-head">
            <div className="ecc-eyebrow">How It Works</div>
            <h2 className="ecc-section-title">Five-Document Export Compliance Workflow</h2>
            <p className="ecc-section-sub">
              From raw PDF upload to downloadable customs audit certificate in five automated stages.
            </p>
          </div>

          <div className="ecc-steps-grid">
            {WORKFLOW_STEPS.map((st) => {
              const Icon = st.icon;
              return (
                <div key={st.step} className="ecc-step-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="ecc-step-num">{st.step}</span>
                    <Icon size={20} color="#0D9488" />
                  </div>
                  <h3 style={{ margin: '4px 0 0 0', fontSize: '15.5px', fontWeight: 700, color: '#102A43' }}>
                    {st.title}
                  </h3>
                  <p style={{ margin: 0, fontSize: '13px', color: '#475569', lineHeight: 1.55 }}>
                    {st.detail}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 5. Trust & Technology Section + About Us */}
      <section id="about-us" className="ecc-section ecc-section-alt">
        <div className="ecc-container">
          <div className="ecc-section-head">
            <div className="ecc-eyebrow">Trust &amp; Architecture</div>
            <h2 className="ecc-section-title">Enterprise Stack Powering Every Audit</h2>
            <p className="ecc-section-sub">
              Export Customs Compliance pairs modern LLM intelligence with deterministic Python compliance engines and authenticated cloud storage.
            </p>
          </div>

          <div className="ecc-tech-grid" style={{ marginBottom: '48px' }}>
            {TECHNOLOGIES.map((tech) => {
              const Icon = tech.icon;
              return (
                <div key={tech.name} className="ecc-tech-card">
                  <div
                    style={{
                      width: '42px',
                      height: '42px',
                      margin: '0 auto 10px auto',
                      borderRadius: '10px',
                      background: '#EAF2F8',
                      color: '#102A43',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={20} />
                  </div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#102A43' }}>
                    {tech.name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#456B8B', marginTop: '4px' }}>
                    {tech.role}
                  </div>
                </div>
              );
            })}
          </div>

          <div id="contact" className="ecc-about-grid">
            <div className="ecc-panel" style={{ background: 'linear-gradient(155deg, #102A43 0%, #1E3A5F 100%)', color: '#ffffff' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em', color: '#9FBAD0', textTransform: 'uppercase', marginBottom: '10px' }}>
                About Us
              </div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '24px', fontWeight: 800 }}>
                Designed for Exporters, CHAs &amp; Trade Compliance Teams
              </h3>
              <p style={{ margin: '0 0 20px 0', fontSize: '14.5px', color: '#EAF2F8', lineHeight: 1.7 }}>
                Manual reconciliation across Commercial Invoices, Packing Lists, Purchase Orders, Shipping Bills, and Certificates of Origin creates costly customs holds. Export Customs Compliance detects mismatches, tax ID anomalies, and statutory gaps before filing.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13.5px', color: '#EAF2F8' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Mail size={16} color="#9FBAD0" />
                  <span>compliance@exportcustoms.app</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <MapPin size={16} color="#9FBAD0" />
                  <span>Indian Export Documentation · DGFT &amp; ICEGATE Workflow</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Clock size={16} color="#9FBAD0" />
                  <span>Automated Pre-Filing Verification &amp; Audit Reporting</span>
                </div>
              </div>
            </div>

            <div className="ecc-panel">
              <div style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em', color: '#0D9488', textTransform: 'uppercase', marginBottom: '8px' }}>
                Contact Compliance Support
              </div>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '21px', fontWeight: 800, color: '#102A43' }}>
                Request Onboarding or Technical Support
              </h3>

              {contactSent ? (
                <div
                  style={{
                    padding: '16px',
                    borderRadius: '10px',
                    backgroundColor: '#CCFBF1',
                    border: '1px solid #99F6E4',
                    color: '#0F766E',
                    fontSize: '14px',
                  }}
                >
                  <strong>Thank you!</strong> Your inquiry has been noted. You can also sign in directly to launch the Export Compliance Workspace.
                </div>
              ) : (
                <form onSubmit={handleContactSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <input
                    type="text"
                    required
                    placeholder="Full Name / Company"
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '14px',
                      color: '#1E293B',
                    }}
                  />
                  <input
                    type="email"
                    required
                    placeholder="Work Email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '14px',
                      color: '#1E293B',
                    }}
                  />
                  <textarea
                    required
                    rows={3}
                    placeholder="Tell us about your export documentation workflow..."
                    value={contactMessage}
                    onChange={(e) => setContactMessage(e.target.value)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '14px',
                      color: '#1E293B',
                      resize: 'vertical',
                      fontFamily: 'inherit',
                    }}
                  />
                  <button type="submit" className="ecc-btn ecc-btn-primary">
                    Send Inquiry
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 6. Footer */}
      <footer className="ecc-footer">
        <div className="ecc-container">
          <div className="ecc-footer-grid">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <div className="ecc-brand-mark" aria-hidden="true">
                  <ShieldCheck size={20} />
                </div>
                <span style={{ fontSize: '15px', fontWeight: 800, letterSpacing: '0.04em', color: '#FFFFFF' }}>
                  EXPORT CUSTOMS COMPLIANCE
                </span>
              </div>
              <p style={{ margin: 0, fontSize: '13.5px', color: '#94A3B8', maxWidth: '380px', lineHeight: 1.65 }}>
                Intelligent Document Verification &amp; Compliance Auditing. Automating export PDF extraction, cross-document validation, fraud screening, and statutory customs checks.
              </p>
            </div>

            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Navigation
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <a href="#home" className="ecc-footer-link">Home</a>
                <a href="#features" className="ecc-footer-link">Features</a>
                <a href="#how-it-works" className="ecc-footer-link">How It Works</a>
                <a href="#about-us" className="ecc-footer-link">About Us</a>
                <a href="#contact" className="ecc-footer-link">Contact</a>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Access &amp; Contact
              </div>
              <div style={{ fontSize: '13.5px', color: '#94A3B8', lineHeight: 1.7, marginBottom: '14px' }}>
                Email: compliance@exportcustoms.app
                <br />
                Authentication: Supabase JWT Auth
              </div>
              <button
                type="button"
                onClick={handleNavLogin}
                className="ecc-btn ecc-btn-primary"
                style={{ padding: '8px 16px', fontSize: '13px' }}
              >
                {isAuthenticated ? 'Open Dashboard' : 'Sign In'}
              </button>
            </div>
          </div>

          <div
            style={{
              paddingTop: '22px',
              display: 'flex',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '10px',
              fontSize: '12.5px',
              color: '#94A3B8',
            }}
          >
            <span>&copy; 2026 EXPORT CUSTOMS COMPLIANCE. All rights reserved.</span>
            <span>Intelligent Document Verification &amp; Compliance Auditing</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
