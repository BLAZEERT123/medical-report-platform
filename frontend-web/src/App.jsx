import React, { useState, useEffect } from 'react';
import { Hospital, UploadCloud, MessageSquare, Activity, Database, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import UploadTab from './components/UploadTab';
import QATab from './components/QATab';
import TrendsTab from './components/TrendsTab';
import './index.css';

const BACKEND_URL = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [health, setHealth] = useState(false);
  const [stats, setStats] = useState({ report_chunks: 0, reference_corpus: 0 });
  const [reports, setReports] = useState([]);
  
  // Shared state
  const [uploadedReport, setUploadedReport] = useState(null);

  useEffect(() => {
    fetchHealth();
    fetchStats();
    fetchReports();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/health`);
      if (res.ok) setHealth(true);
    } catch {
      setHealth(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/qa/store-stats`);
      if (res.ok) setStats(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchReports = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/reports/`);
      if (res.ok) setReports(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <Hospital size={48} color="var(--primary)" style={{ filter: 'drop-shadow(0 0 10px rgba(0, 240, 255, 0.5))' }} />
          <h2 style={{ marginTop: '1rem', letterSpacing: '1px' }}>MedIntel</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Medical Report Intelligence</p>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <div className="glass-card" style={{ padding: '0.75rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: health ? 'var(--status-normal)' : 'var(--status-abnormal)', boxShadow: `0 0 10px ${health ? 'var(--status-normal)' : 'var(--status-abnormal)'}` }}></div>
            <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>Backend {health ? 'Connected' : 'Offline'}</span>
          </div>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h4 style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>Vector Store Status</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="glass-card" style={{ padding: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <FileText size={16} color="var(--primary)" />
                <span style={{ fontSize: '0.85rem' }}>Report Chunks</span>
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{stats.report_chunks}</div>
            </div>
            <div className="glass-card" style={{ padding: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <Database size={16} color="var(--accent)" />
                <span style={{ fontSize: '0.85rem' }}>Reference Chunks</span>
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{stats.reference_corpus}</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header style={{ marginBottom: '2rem' }}>
          <h1 className="heading-gradient" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Medical Report Intelligence</h1>
          <p style={{ color: 'var(--text-muted)' }}>Upload lab reports → Extract structured data → Ask questions with grounded citations</p>
        </header>

        {/* Tabs Navigation */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
          <button 
            className={`btn-secondary ${activeTab === 'upload' ? 'active-tab' : ''}`}
            onClick={() => setActiveTab('upload')}
            style={{ 
              background: activeTab === 'upload' ? 'rgba(255, 255, 255, 0.1)' : 'var(--surface)',
              borderColor: activeTab === 'upload' ? 'rgba(255, 255, 255, 0.2)' : 'var(--border)',
              display: 'flex', alignItems: 'center', gap: '8px'
            }}
          >
            <UploadCloud size={18} /> Upload & Analyze
          </button>
          <button 
            className={`btn-secondary ${activeTab === 'qa' ? 'active-tab' : ''}`}
            onClick={() => setActiveTab('qa')}
            style={{ 
              background: activeTab === 'qa' ? 'rgba(255, 255, 255, 0.1)' : 'var(--surface)',
              borderColor: activeTab === 'qa' ? 'rgba(255, 255, 255, 0.2)' : 'var(--border)',
              display: 'flex', alignItems: 'center', gap: '8px'
            }}
          >
            <MessageSquare size={18} /> Q&A with Sources
          </button>
          <button 
            className={`btn-secondary ${activeTab === 'trends' ? 'active-tab' : ''}`}
            onClick={() => setActiveTab('trends')}
            style={{ 
              background: activeTab === 'trends' ? 'rgba(255, 255, 255, 0.1)' : 'var(--surface)',
              borderColor: activeTab === 'trends' ? 'rgba(255, 255, 255, 0.2)' : 'var(--border)',
              display: 'flex', alignItems: 'center', gap: '8px'
            }}
          >
            <Activity size={18} /> Longitudinal Trends
          </button>
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <UploadTab 
                backendUrl={BACKEND_URL} 
                uploadedReport={uploadedReport}
                setUploadedReport={setUploadedReport}
                onAnalyzeComplete={() => {
                  fetchReports();
                  fetchStats();
                }}
              />
            </motion.div>
          )}
          {activeTab === 'qa' && (
            <motion.div
              key="qa"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <QATab backendUrl={BACKEND_URL} />
            </motion.div>
          )}
          {activeTab === 'trends' && (
            <motion.div
              key="trends"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <TrendsTab backendUrl={BACKEND_URL} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
