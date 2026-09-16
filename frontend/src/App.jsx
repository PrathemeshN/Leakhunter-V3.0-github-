import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import logoImg from './assets/logo.png';
import heroImg from './assets/hero.png';

const API_BASE_URL = '/api/v1';

export default function App() {
  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('lh_token'));
  const [token, setToken] = useState(localStorage.getItem('lh_token') || '');
  const [userRole, setUserRole] = useState(localStorage.getItem('lh_role') || '');
  const [userEmail, setUserEmail] = useState(localStorage.getItem('lh_email') || '');
  
  // Login Form
  const [isRegistering, setIsRegistering] = useState(false);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');

  // App Layout State
  const [activeTab, setActiveTab] = useState('threat-center'); // threat-center, search-explorer, scraper-manager, ml-classifier
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [stats, setStats] = useState({
    totalBreaches: 0,
    totalRecords: 0,
    avgSeverity: 0,
    classifications: { credentials: 0, pii: 0, financial: 0, health: 0, corporate: 0, other: 0 },
    timeline: []
  });
  
  // Data State
  const [breaches, setBreaches] = useState([]);
  const [scrapers, setScrapers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  
  // Scraper Form
  const [scraperName, setScraperName] = useState('');
  const [scraperUrl, setScraperUrl] = useState('');
  const [scraperType, setScraperType] = useState('dark_web');
  
  // Retrain Form
  const [trainTexts, setTrainTexts] = useState('');
  const [trainLabels, setTrainLabels] = useState('');
  const [trainStatus, setTrainStatus] = useState('');

  // Selected Detail Modal
  const [selectedBreach, setSelectedBreach] = useState(null);
  
  // Toast notifications
  const [toasts, setToasts] = useState([]);

  // Ref for WebSocket
  const wsRef = useRef(null);

  // Trigger Toast Alert
  const showToast = (title, message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  };

  // Check Backend Status & Load data
  useEffect(() => {
    checkConnectionAndLoad();
    const interval = setInterval(checkConnectionAndLoad, 10000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Connect WebSockets for Real-time Alerts
  useEffect(() => {
    if (isAuthenticated) {
      connectWebSocket();
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [isAuthenticated]);

  const checkConnectionAndLoad = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`);
      if (response.ok) {
        setIsBackendOnline(true);
        const data = await response.json();
        setStats(data);
        if (isAuthenticated) {
          loadBreaches();
          loadScrapers();
        }
      } else {
        setIsBackendOnline(false);
      }
    } catch (e) {
      setIsBackendOnline(false);
    }
  };

  const loadBreaches = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await fetch(`${API_BASE_URL}/breaches`, { headers });
      if (response.ok) {
        const data = await response.json();
        setBreaches(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadScrapers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/scrapers`);
      if (response.ok) {
        const data = await response.json();
        setScrapers(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const connectWebSocket = () => {
    try {
      if (wsRef.current) wsRef.current.close();
      
      const ws = new WebSocket('ws://localhost:8000/api/v1/alerts/ws');
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.event === 'new_breach') {
          const newBreach = payload.data;
          showToast('CRITICAL LEAK INGESTED', newBreach.title);
          // Refresh statistics and threat feed lists
          checkConnectionAndLoad();
        }
      };

      ws.onclose = () => {
        console.log('WebSocket closed. Reconnecting...');
        setTimeout(connectWebSocket, 5000);
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
    }
  };

  // --- Auth Handlers ---

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', authEmail);
      formData.append('password', authPassword);

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('lh_token', data.access_token);
        localStorage.setItem('lh_role', data.role);
        localStorage.setItem('lh_email', data.email);
        setToken(data.access_token);
        setUserRole(data.role);
        setUserEmail(data.email);
        setIsAuthenticated(true);
        showToast('Access Granted', `Welcome back, ${data.email}`);
      } else {
        setAuthError('Authentication failed. Invalid credentials.');
      }
    } catch (e) {
      setAuthError('API server unreachable. Verify backend is running.');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });

      if (response.ok) {
        setIsRegistering(false);
        setAuthPassword('');
        showToast('Registration Successful', 'You can now sign in.');
      } else {
        const err = await response.json();
        setAuthError(err.detail || 'Registration failed.');
      }
    } catch (e) {
      setAuthError('API server unreachable.');
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    setIsAuthenticated(false);
    setToken('');
    setUserRole('');
    setUserEmail('');
    showToast('Session Ended', 'Logged out successfully.');
  };

  // --- Search Handler ---

  const handleDownloadReport = (breach) => {
    const report = {
      meta: {
        generated_by: "LeakHunter V3",
        timestamp: new Date().toISOString()
      },
      breach_id: breach.id,
      title: breach.title,
      discovered_date: breach.discovered_date,
      source: {
        url: breach.original_url,
        reference: breach.source_reference,
      },
      metrics: {
        severity_score: breach.severity_score,
        confidence_score: breach.confidence_score,
        record_count: breach.record_count,
        verified_authentic: breach.confirmed_authentic === 1
      },
      raw_post_content: breach.raw_content || breach.description,
      extracted_intelligence: breach.raw_data
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `LeakHunter_Intel_${breach.id?.substring(0,8) || 'Report'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Download Started', 'Threat intel JSON report generated.');
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(searchQuery)}`, { headers });
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
      } else {
        showToast('Search Failed', 'Failed to retrieve Elasticsearch records.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  // --- Admin Register Scraper ---

  const handleAddScraper = async (e) => {
    e.preventDefault();
    try {
      const headers = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      };
      const payload = {
        name: scraperName,
        url: scraperUrl,
        source_type: scraperType,
      };
      const response = await fetch(`${API_BASE_URL}/scrapers`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setScraperName('');
        setScraperUrl('');
        loadScrapers();
        showToast('Scraper Added', `Scraper '${payload.name}' registered.`);
      } else {
        showToast('Registration Failed', 'A scraper with this name may already exist.');
      }
    } catch (e) {
      console.error(e);
    }
  };

  // --- Simulate Scraped Payload Submission ---

  const handleSimulateScrape = async () => {
    if (!scrapers.length) {
      showToast('Simulation Cancelled', 'Please register at least one Scraper Source first.');
      return;
    }
    const sampleLeaks = [
      {
        title: "Apex Aerospace Decryption Key Comp",
        description: "Dark web post containing internal SSH keys and decrypted archives from apex-aerospace.com structural designs.",
        raw_content: "Hacker: lockbit_official. Leaked design schemas of turbine core. ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8z9... contact administrator@apex-aerospace.com for details.",
        original_url: "http://lockbitw7272x.onion/apex-leak-v2"
      },
      {
        title: "Medicare Plus Health Records Compile",
        description: "Aggregated user patient records sold on forums. Contains patient names and national identifiers.",
        raw_content: "Patient records dump. Name: Rajesh Kumar, Aadhaar Card: 4589 1236 7894, DOB: 12-05-1994, Address: Sector-15 Noida, UP. Email: rajesh@gmail.com",
        original_url: "http://breachforums.onion/medicare-db"
      },
      {
        title: "Hacker Signature Credentials",
        description: "Hacker credentials dump containing credit card formats.",
        raw_content: "Leaked by kuro_hacker: admin:password123, cardholder: Prathamesh P Nandgaonkar, Card: 4111 1111 1111 1111, CVV: 123, EXP: 12/28. Email: admin@leakhunter.ai",
        original_url: "tg://join?invite=leak_intel_channel"
      }
    ];

    const randomPayload = sampleLeaks[Math.floor(Math.random() * sampleLeaks.length)];
    
    try {
      const payload = {
        source_id: scrapers[0].id,
        title: randomPayload.title,
        description: randomPayload.description,
        raw_content: randomPayload.raw_content,
        original_url: randomPayload.original_url,
        source_reference: `SIM-${Math.floor(Math.random() * 10000)}`,
        record_count: Math.floor(Math.random() * 5000) + 10
      };
      
      const response = await fetch(`${API_BASE_URL}/simulate-scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        showToast('Scrape Simulated', 'Mock leak published to Broker queue. Ingestion pipeline is running...');
      } else {
        showToast('Simulation Failed', 'Could not push payload to backend.');
      }
    } catch (e) {
      console.error(e);
    }
  };

  // --- Classifier Retraining ---

  const handleRetrain = async (e) => {
    e.preventDefault();
    setTrainStatus('Uploading training dataset...');
    try {
      const texts = trainTexts.split('\n').filter((t) => t.trim().length > 5);
      const labels = trainLabels.split('\n').map((l) => l.trim().toLowerCase()).filter((l) => l.length > 0);
      
      if (texts.length !== labels.length) {
        setTrainStatus('Error: Number of training lines must exactly match labels lines.');
        return;
      }

      const headers = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      };
      const response = await fetch(`${API_BASE_URL}/train`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ texts, labels }),
      });

      if (response.ok) {
        setTrainStatus('Model retrained successfully. Model weights updated.');
        setTrainTexts('');
        setTrainLabels('');
        checkConnectionAndLoad();
      } else {
        const err = await response.json();
        setTrainStatus(`Retrain failed: ${err.detail || 'Internal server error'}`);
      }
    } catch (e) {
      setTrainStatus('Error connecting to retraining API.');
    }
  };

  // Helper for Severity Color Badges
  const getSeverityBadge = (score) => {
    if (score >= 90) return <span className="badge critical">CRITICAL ({score})</span>;
    if (score >= 75) return <span className="badge high">HIGH ({score})</span>;
    if (score >= 50) return <span className="badge medium">MEDIUM ({score})</span>;
    return <span className="badge low">LOW ({score})</span>;
  };

  // --- RENDERS ---

  if (!isAuthenticated) {
    return (
      <div className="login-overlay">
        <form className="login-card" onSubmit={isRegistering ? handleRegister : handleLogin}>
          <div className="login-header">
            <img src={logoImg} alt="LeakHunter AI" className="logo-image-login" />
            <p className="login-subtitle">
              {isRegistering
                ? 'Create a security analyst workspace'
                : 'Automated Breach Detection & Forensics Layer'}
            </p>
          </div>

          {authError && (
            <div style={{ color: 'var(--color-danger)', fontSize: '0.85rem', marginBottom: '16px', textAlign: 'center' }}>
              {authError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Analyst Email</label>
            <input
              type="email"
              className="form-input"
              required
              placeholder="e.g. analyst@leakhunter.ai"
              value={authEmail}
              onChange={(e) => setAuthEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password Key</label>
            <input
              type="password"
              className="form-input"
              required
              placeholder="••••••••"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn">
            {isRegistering ? 'Register Analyst' : 'Authenticate Session'}
          </button>

          <p className="login-footer-text">
            {isRegistering ? 'Have an account?' : "Don't have an account?"}{' '}
            <span className="login-toggle" onClick={() => setIsRegistering(!isRegistering)}>
              {isRegistering ? 'Log in' : 'Register now'}
            </span>
          </p>
        </form>
      </div>
    );
  }

  // Generate SVG timeline points dynamically
  const getTimelinePoints = () => {
    if (!stats.timeline || stats.timeline.length === 0) return "";
    const width = 500;
    const height = 150;
    const maxVal = Math.max(...stats.timeline.map((t) => t.count), 5);
    
    return stats.timeline.map((t, idx) => {
      const x = (idx / (stats.timeline.length - 1 || 1)) * (width - 40) + 20;
      const y = height - (t.count / maxVal) * (height - 40) - 20;
      return `${x},${y}`;
    }).join(" ");
  };

  return (
    <div className="app-container">
      {/* Sidebar navigation */}
      <div className="sidebar">
        <div className="logo-section" style={{ justifyContent: 'center', marginBottom: '24px' }}>
          <img src={logoImg} alt="LeakHunter AI" className="logo-image-sidebar" />
        </div>

        <div className="nav-links">
          <div
            className={`nav-item ${activeTab === 'threat-center' ? 'active' : ''}`}
            onClick={() => setActiveTab('threat-center')}
          >
            {/* Inline SVG Dashboard Icon */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
            Threat Center
          </div>

          <div
            className={`nav-item ${activeTab === 'search-explorer' ? 'active' : ''}`}
            onClick={() => setActiveTab('search-explorer')}
          >
            {/* Inline SVG Search Icon */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            ES Search Explorer
          </div>

          <div
            className={`nav-item ${activeTab === 'scraper-manager' ? 'active' : ''}`}
            onClick={() => setActiveTab('scraper-manager')}
          >
            {/* Inline SVG Terminal/Scraper Icon */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            Scrapers Manager
          </div>

          <div
            className={`nav-item ${activeTab === 'ml-classifier' ? 'active' : ''}`}
            onClick={() => setActiveTab('ml-classifier')}
          >
            {/* Inline SVG CPU/ML Icon */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/></svg>
            Classifier Trainer
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="user-badge">
            <div className="user-avatar">{userEmail[0].toUpperCase()}</div>
            <div className="user-info">
              <span className="user-name">{userEmail}</span>
              <span className="user-role">{userRole.toUpperCase()}</span>
            </div>
          </div>
          <button className="btn btn-secondary" style={{ padding: '8px 12px', fontSize: '0.85rem' }} onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        <div className="topbar">
          <h2 className="page-title">
            {activeTab === 'threat-center' && 'Breach Threat Center'}
            {activeTab === 'search-explorer' && 'Elasticsearch Threat Index'}
            {activeTab === 'scraper-manager' && 'Dark Web Scrapers & Sources'}
            {activeTab === 'ml-classifier' && 'Custom Classifier ML Pipeline'}
          </h2>

          <div className="status-indicator">
            <span className={`status-dot ${isBackendOnline ? 'online' : 'offline'}`} />
            API & Pipeline Node: {isBackendOnline ? 'ONLINE' : 'OFFLINE'}
          </div>
        </div>

        {/* Tab contents */}
        <div className="page-body">
          {activeTab === 'threat-center' && (
            <div className="animate-slide">
              {/* Stats Widgets */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-info">
                    <span className="stat-title">Threat Sources Scraped</span>
                    <span className="stat-value">{scrapers.length}</span>
                  </div>
                  <div className="stat-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-info">
                    <span className="stat-title">Total Detected Leaks</span>
                    <span className="stat-value">{stats.totalBreaches}</span>
                  </div>
                  <div className="stat-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-info">
                    <span className="stat-title">Records Analyzed</span>
                    <span className="stat-value">{(stats.totalRecords || 0).toLocaleString()}</span>
                  </div>
                  <div className="stat-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  </div>
                </div>

                <div className="stat-card risk">
                  <div className="stat-info">
                    <span className="stat-title">Average Risk Score</span>
                    <span className="stat-value">{stats.avgSeverity}%</span>
                  </div>
                  <div className="stat-icon" style={{ borderColor: 'rgba(255, 23, 68, 0.2)', color: 'var(--color-danger)' }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M8.56 2.75c4.37-1 9 .31 11.5 4.31M2 12c0 2.21.9 4.21 2.34 5.66M21.25 8.56c1 4.37-.31 9-4.31 11.5M12 22c-2.21 0-4.21-.9-5.66-2.34"/></svg>
                  </div>
                </div>
              </div>

              {/* Visualizations row */}
              <div className="visuals-grid">
                {/* Timeline SVG Chart */}
                <div className="panel-card">
                  <div className="panel-header">
                    <h3 className="panel-title">Data Leak Ingestion History (30 Days)</h3>
                  </div>
                  <div className="chart-container">
                    {stats.timeline.length > 1 ? (
                      <svg width="100%" height="150" viewBox="0 0 500 150" style={{ overflow: 'visible' }}>
                        <defs>
                          <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        {/* Area path */}
                        <path
                          d={`M 20,130 L ${getTimelinePoints()} L 480,130 Z`}
                          fill="url(#chartGrad)"
                        />
                        {/* Line path */}
                        <polyline
                          fill="none"
                          stroke="var(--color-primary)"
                          strokeWidth="2.5"
                          points={getTimelinePoints()}
                        />
                        {/* Interactive dots */}
                        {stats.timeline.map((t, idx) => {
                          const maxVal = Math.max(...stats.timeline.map((s) => s.count), 5);
                          const x = (idx / (stats.timeline.length - 1)) * 460 + 20;
                          const y = 150 - (t.count / maxVal) * 110 - 20;
                          return (
                            <g key={idx}>
                              <circle cx={x} cy={y} r="4" fill="#000" stroke="var(--color-primary)" strokeWidth="2" />
                              <text x={x} y={y - 8} fill="var(--text-secondary)" fontSize="8" textAnchor="middle">{t.count}</text>
                              <text x={x} y="145" fill="var(--text-muted)" fontSize="7" textAnchor="middle">{t.date.slice(-5)}</text>
                            </g>
                          );
                        })}
                      </svg>
                    ) : (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: 'auto' }}>No history records available yet.</div>
                    )}
                  </div>
                </div>

                {/* Categories SVG Donut Chart */}
                <div className="panel-card">
                  <div className="panel-header">
                    <h3 className="panel-title">Extracted PII Classifications</h3>
                  </div>
                  <div className="donut-chart-box">
                    <svg width="120" height="120" viewBox="0 0 42 42" className="donut">
                      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--border-color)" strokeWidth="4"></circle>
                      {/* Segment 1: Credentials (Blue) */}
                      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--color-info)" strokeWidth="4" 
                        strokeDasharray="40 60" strokeDashoffset="25"></circle>
                      {/* Segment 2: PII (Teal) */}
                      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--color-primary)" strokeWidth="4" 
                        strokeDasharray="30 70" strokeDashoffset="85"></circle>
                      {/* Segment 3: Financial (Red) */}
                      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--color-danger)" strokeWidth="4" 
                        strokeDasharray="20 80" strokeDashoffset="55"></circle>
                      {/* Segment 4: Health (Amber) */}
                      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--color-warning)" strokeWidth="4" 
                        strokeDasharray="10 90" strokeDashoffset="35"></circle>
                    </svg>

                    <div className="donut-legend">
                      <div className="legend-item">
                        <span className="legend-dot" style={{ backgroundColor: 'var(--color-info)' }} />
                        Credentials ({stats.classifications.credentials})
                      </div>
                      <div className="legend-item">
                        <span className="legend-dot" style={{ backgroundColor: 'var(--color-primary)' }} />
                        PII / Identity ({stats.classifications.pii})
                      </div>
                      <div className="legend-item">
                        <span className="legend-dot" style={{ backgroundColor: 'var(--color-danger)' }} />
                        Financial ({stats.classifications.financial})
                      </div>
                      <div className="legend-item">
                        <span className="legend-dot" style={{ backgroundColor: 'var(--color-warning)' }} />
                        Health ({stats.classifications.health})
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Threat Feed List */}
              <div className="panel-card" style={{ minHeight: '350px' }}>
                <div className="feed-header">
                  <span>Active Incident Feed</span>
                  <div className="live-badge">
                    <span className="live-dot" /> LIVE ALERT DISPATCHER ACTIVE
                  </div>
                </div>

                <div className="threat-feed-container">
                  {breaches.length > 0 ? (
                    breaches.map((breach) => (
                      <div key={breach.id} className="threat-card" onClick={() => setSelectedBreach(breach)}>
                        <div className="threat-meta">
                          <span className="threat-title">{breach.title}</span>
                          <span className="threat-date">
                            {new Date(breach.discovered_date).toLocaleString()}
                          </span>
                        </div>
                        <div className="threat-summary">
                          {getSeverityBadge(breach.severity_score)}
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Records: <strong>{(breach.record_count || 0).toLocaleString()}</strong>
                          </span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Domains: <strong>{(breach.affected_domains || []).join(', ') || 'N/A'}</strong>
                          </span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Confidence:{' '}
                            <strong style={{
                                color: breach.confidence_score >= 70 ? 'var(--color-success)' : breach.confidence_score >= 40 ? 'var(--color-warning)' : 'var(--color-danger)'
                            }}>
                              {breach.confidence_score ? breach.confidence_score.toFixed(1) + '%' : 'N/A'}
                            </strong>
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>
                      No data breaches indexed yet. Go to 'Scrapers Manager' to run a simulation crawl!
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'search-explorer' && (
            <div className="animate-slide">
              <form onSubmit={handleSearch} style={{ display: 'flex', gap: '16px', marginBottom: '32px' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ flexGrow: 1 }}
                  required
                  placeholder="Query Elasticsearch index by domain (e.g. apex-aerospace.com) or threat actor handle (e.g. lockbit_official)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <button type="submit" className="btn" style={{ width: '140px' }} disabled={isSearching}>
                  {isSearching ? 'Searching...' : 'Search Index'}
                </button>
              </form>

              <div className="panel-card" style={{ minHeight: '400px' }}>
                <div className="feed-header">Search Results</div>
                <div className="threat-feed-container">
                  {searchResults.length > 0 ? (
                    searchResults.map((hit) => (
                      <div key={hit.id} className="threat-card" onClick={() => setSelectedBreach(hit)}>
                        <div className="threat-meta">
                          <span className="threat-title">{hit.title}</span>
                          <span className="threat-date">
                            {new Date(hit.discovered_date).toLocaleDateString()}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '4px 0' }}>
                          {hit.description}
                        </p>
                        <div className="threat-summary">
                          {getSeverityBadge(hit.severity_score)}
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            Category: <strong>{hit.data_types.join(', ')}</strong>
                          </span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            Target Domains: <strong>{(hit.affected_domains || []).join(', ') || 'N/A'}</strong>
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>
                      {searchQuery ? 'No documents matched search criteria.' : 'Enter a query string above to scan indexed documents.'}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'scraper-manager' && (
            <div className="animate-slide admin-row">
              {/* Register Scraper Form */}
              <div className="panel-card">
                <div className="panel-header">
                  <h3 className="panel-title">Register Scraper Feed Target</h3>
                </div>
                <form onSubmit={handleAddScraper} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div className="form-group">
                    <label className="form-label">Scraper Feed Name</label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      placeholder="e.g. BreachForums Dark Web Crawler"
                      value={scraperName}
                      onChange={(e) => setScraperName(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Target .onion / API Endpoint URL</label>
                    <input
                      type="text"
                      className="form-input"
                      required
                      placeholder="e.g. http://breachforums.onion/leaks"
                      value={scraperUrl}
                      onChange={(e) => setScraperUrl(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Feed Ingestion Layer Type</label>
                    <select
                      className="form-input"
                      value={scraperType}
                      onChange={(e) => setScraperType(e.target.value)}
                    >
                      <option value="dark_web">Dark Web Forum / Tor Onion</option>
                      <option value="telegram">Telegram Intel Channel</option>
                      <option value="api">External Threat Vendor API</option>
                      <option value="web_scrape">Clearnet OSINT Site</option>
                    </select>
                  </div>

                  <button type="submit" className="btn">
                    Register Scraper Feed
                  </button>
                </form>
              </div>

              {/* Scrapers List & Simulator */}
              <div className="panel-card">
                <div className="panel-header">
                  <h3 className="panel-title">Crawler Control & Simulation Hub</h3>
                </div>
                
                <div style={{ marginBottom: '24px' }}>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '16px' }}>
                    Publish a simulated dark-web scraped dump directly to the event broker (Redis/Kafka) queue to trigger the full processing pipeline.
                  </p>
                  <button onClick={handleSimulateScrape} className="btn" style={{ background: 'var(--color-success)' }}>
                    Trigger Simulated Crawl
                  </button>
                </div>

                <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '12px' }}>
                  Active Registered Feeds
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {scrapers.length > 0 ? (
                    scrapers.map((s) => (
                      <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                        <div>
                          <strong style={{ fontSize: '0.9rem' }}>{s.name}</strong>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.url}</div>
                        </div>
                        <span className="badge low" style={{ textTransform: 'uppercase' }}>{s.source_type}</span>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No scrapers configured yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ml-classifier' && (
            <div className="animate-slide admin-row">
              {/* Training panel */}
              <div className="panel-card">
                <div className="panel-header">
                  <h3 className="panel-title">Retrain Classification Pipeline</h3>
                </div>
                <form onSubmit={handleRetrain} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="form-group">
                    <label className="form-label">Training Input Documents (One sample per line)</label>
                    <textarea
                      className="form-input textarea-input"
                      required
                      placeholder="e.g. compromised credit card information billing cardholder name 4111 2222&#10;leaked username password md5 crypt hash credentials admin:pass"
                      value={trainTexts}
                      onChange={(e) => setTrainTexts(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Corresponding Labels (One label per line: credentials, pii, financial, health, corporate)</label>
                    <textarea
                      className="form-input"
                      style={{ minHeight: '100px' }}
                      required
                      placeholder="e.g. financial&#10;credentials"
                      value={trainLabels}
                      onChange={(e) => setTrainLabels(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="btn">
                    Retrain Model Pipeline
                  </button>
                  
                  {trainStatus && (
                    <div style={{ color: 'var(--color-primary)', fontSize: '0.85rem', marginTop: '8px' }}>
                      {trainStatus}
                    </div>
                  )}
                </form>
              </div>

              {/* Status and weights info */}
              <div className="panel-card">
                <div className="panel-header">
                  <h3 className="panel-title">Classifier Engine Specifications</h3>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  <p>
                    LeakHunter V2 uses an event-driven **scikit-learn** model featuring **TF-IDF text vectorization** combined with a **Random Forest Classifier** to assess data leaks.
                  </p>
                  <div>
                    <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Threat Category Weights</h4>
                    <ul style={{ listStyleType: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <li>💳 Financial Data Compromise: <strong style={{ color: 'var(--color-danger)' }}>95% Risk</strong></li>
                      <li>🏥 Healthcare Patient Records: <strong style={{ color: 'var(--color-warning)' }}>90% Risk</strong></li>
                      <li>🔑 Authentication Credentials: <strong style={{ color: 'var(--color-warning)' }}>85% Risk</strong></li>
                      <li>🏢 Corporate Designs / Trade Secrets: <strong style={{ color: 'var(--color-info)' }}>80% Risk</strong></li>
                      <li>👤 Personally Identifiable Information: <strong style={{ color: 'var(--color-primary)' }}>75% Risk</strong></li>
                    </ul>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Model updates are saved incrementally as `.joblib` serialized pipelines on the processing nodes, taking effect immediately for all subsequent scraped payloads.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Selected Breach Detail Modal */}
      {selectedBreach && (
        <div className="modal-overlay" onClick={() => setSelectedBreach(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="page-title">{selectedBreach.title}</h3>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-primary" style={{ padding: '8px 16px', fontSize: '0.85rem' }} onClick={() => handleDownloadReport(selectedBreach)}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px', verticalAlign: 'middle' }}>
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  Export Intel JSON
                </button>
                <button className="btn btn-secondary" style={{ width: '40px', padding: '0' }} onClick={() => setSelectedBreach(null)}>X</button>
              </div>
            </div>
            
            <div className="modal-body">
              <div>
                <h4 className="modal-section-title">Breach Metadata</h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '12px' }}>
                  {selectedBreach.description}
                </p>
                <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                  <div>Risk Severity: {getSeverityBadge(selectedBreach.severity_score)}</div>
                  <div>Authenticity: 
                    <span style={{ marginLeft: '6px', fontWeight: 'bold' }}>
                      {selectedBreach.confirmed_authentic === 1 ? '✅ VERIFIED AUTHENTIC' : '⚠️ UNVERIFIED INTEL'}
                    </span>
                  </div>
                  <div>Record Count: <strong>{(selectedBreach.record_count || 0).toLocaleString()}</strong></div>
                  <div>Confidence Score: 
                    <span style={{ 
                      marginLeft: '6px', 
                      fontWeight: 'bold', 
                      color: selectedBreach.confidence_score >= 70 ? 'var(--color-success)' : selectedBreach.confidence_score >= 40 ? 'var(--color-warning)' : 'var(--color-danger)'
                    }}>
                      {selectedBreach.confidence_score ? selectedBreach.confidence_score.toFixed(1) + '%' : 'Unscored'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Source & Author Details */}
              <div style={{ marginTop: '24px', padding: '16px', backgroundColor: 'var(--bg-card-hover)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <h4 className="modal-section-title" style={{ marginBottom: '12px' }}>Scrape Source / Author Details</h4>
                {(() => {
                  let username = 'Unknown';
                  let authorName = 'Anonymous Source';
                  let userId = 'HIDDEN';
                  let avatarUrl = `https://ui-avatars.com/api/?name=Unknown&background=random`;
                  
                  if (selectedBreach.source_reference?.startsWith('telegram')) {
                    const parts = selectedBreach.source_reference.split(':');
                    if (parts.length >= 2) {
                      username = parts[1];
                      authorName = selectedBreach.title.split(':')[0].replace('[Telegram] ', '').trim() || username;
                      userId = `TG-${Math.abs(username.split('').reduce((a,b)=>{a=((a<<5)-a)+b.charCodeAt(0);return a&a},0))}`; // Deterministic pseudo-ID for demo
                      avatarUrl = `https://t.me/i/userpic/320/${username}.jpg`;
                    }
                  } else if (selectedBreach.source_reference?.startsWith('pastebin')) {
                    username = 'Guest_Pastebin';
                    authorName = 'Public Pastebin Upload';
                    userId = 'PB-ANON';
                    avatarUrl = `https://ui-avatars.com/api/?name=Paste+Bin&background=0D121C&color=00e5ff`;
                  } else if (selectedBreach.source_reference?.startsWith('forum')) {
                     username = 'Forum_Actor';
                     authorName = 'Dark Web Forum User';
                     userId = 'DW-UID-XXXX';
                     avatarUrl = `https://ui-avatars.com/api/?name=Forum+Actor&background=ef4444&color=fff`;
                  }

                  return (
                    <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                      <img 
                        src={avatarUrl} 
                        alt="Author Avatar" 
                        style={{ width: '64px', height: '64px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--color-primary)' }}
                        onError={(e) => { e.target.src = `https://ui-avatars.com/api/?name=${username}&background=random`; }}
                      />
                      <div style={{ flexGrow: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
                          <span style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--text-primary)' }}>{authorName}</span>
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>@{username}</span>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                          <strong>User ID:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>{userId}</span>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          <strong>Original Post Path:</strong>{' '}
                          <a href={selectedBreach.original_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-primary)', textDecoration: 'none' }}>
                            {selectedBreach.original_url || 'No URL Available'}
                          </a>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>

              {selectedBreach.raw_data && selectedBreach.raw_data.extracted_pii && (
                <div>
                  <h4 className="modal-section-title">Extracted Sensitive Identifiers</h4>
                  <table className="traceback-table">
                    <thead>
                      <tr>
                        <th>Identifier Type</th>
                        <th>Scraped Matches</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(selectedBreach.raw_data.extracted_pii).map(([key, val]) => (
                        <tr key={key}>
                          <td>{key.replace('_', ' ').toUpperCase()}</td>
                          <td>{Array.isArray(val) ? val.join(', ') : JSON.stringify(val)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selectedBreach.raw_data && selectedBreach.raw_data.traceback && (
                <div>
                  <h4 className="modal-section-title">OSINT Traceback & Attributions</h4>
                  <h5 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px' }}>Domain Infrastructure Lookup:</h5>
                  <table className="traceback-table">
                    <thead>
                      <tr>
                        <th>Affected Domain</th>
                        <th>IP Address</th>
                        <th>Hosting Provider</th>
                        <th>Country</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedBreach.raw_data.traceback.resolved_domains && selectedBreach.raw_data.traceback.resolved_domains.map((rd, i) => (
                        <tr key={i}>
                          <td>{rd.domain}</td>
                          <td>{rd.ip_address}</td>
                          <td>{rd.hosting_provider}</td>
                          <td>{rd.country}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {selectedBreach.raw_data.traceback.actor_correlations && selectedBreach.raw_data.traceback.actor_correlations.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                      <h5 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>Threat Actor Correlations:</h5>
                      <table className="traceback-table">
                        <thead>
                          <tr>
                            <th>Correlated Handle</th>
                            <th>Active Platforms</th>
                            <th>Threat Group Association</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedBreach.raw_data.traceback.actor_correlations.map((ac, i) => (
                            <tr key={i}>
                              <td style={{ color: 'var(--color-danger)', fontWeight: 'bold' }}>{ac.username}</td>
                              <td>{ac.correlated_platforms.join(', ')}</td>
                              <td>{ac.threat_group_affinity}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Toast Alerts Overlay */}
      <div style={{ zIndex: 1000 }}>
        {toasts.map((toast) => (
          <div key={toast.id} className="alert-toast">
            <div className="pulse-active" style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--color-primary)' }} />
            <div className="toast-content">
              <strong style={{ fontSize: '0.85rem', color: 'var(--color-primary)', textTransform: 'uppercase' }}>{toast.title}</strong>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{toast.message}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
