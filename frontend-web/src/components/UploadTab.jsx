import React, { useState, useRef } from 'react';
import { Upload, FileText, AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function UploadTab({ backendUrl, uploadedReport, setUploadedReport, onAnalyzeComplete }) {
  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${backendUrl}/reports/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Analysis failed');
      }
      
      const data = await response.json();
      setUploadedReport(data);
      onAnalyzeComplete();
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div>
      <div className="glass-card" style={{ padding: '2rem', marginBottom: '2rem' }}>
        <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Upload Report</h2>
        
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start' }}>
          <div 
            style={{ 
              flex: 1, 
              border: `2px dashed ${file ? 'var(--primary)' : 'var(--border)'}`, 
              borderRadius: '16px', 
              padding: '2rem', 
              textAlign: 'center',
              background: file ? 'var(--primary-bg)' : 'rgba(0,0,0,0.2)',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
            onClick={() => fileInputRef.current.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              style={{ display: 'none' }} 
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" 
            />
            
            {file ? (
              <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }}>
                <FileText size={48} color="var(--primary)" style={{ margin: '0 auto 1rem' }} />
                <p style={{ fontWeight: 600, color: 'var(--text-main)' }}>{file.name}</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{(file.size / 1024).toFixed(1)} KB</p>
              </motion.div>
            ) : (
              <div>
                <Upload size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem' }} />
                <p style={{ color: 'var(--text-main)', marginBottom: '0.5rem', fontWeight: 500 }}>Click to browse or drag and drop</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Supports: PDF, PNG, JPG, JPEG, TIFF</p>
              </div>
            )}
          </div>
          
          <div style={{ width: '250px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <button 
              className="btn-primary" 
              style={{ width: '100%', padding: '1rem' }}
              onClick={handleAnalyze}
              disabled={!file || isAnalyzing}
            >
              {isAnalyzing ? (
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                  <Upload size={20} />
                </motion.div>
              ) : (
                <><FileText size={20} /> Analyze Report</>
              )}
            </button>
            
            {error && (
              <div style={{ padding: '1rem', background: 'var(--status-abnormal-bg)', color: 'var(--status-abnormal)', borderRadius: '12px', fontSize: '0.85rem', display: 'flex', gap: '8px' }}>
                <AlertCircle size={16} /> {error}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Results Section */}
      <AnimatePresence>
        {uploadedReport && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card" 
            style={{ padding: '2rem' }}
          >
            <ReportResults report={uploadedReport} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ReportResults({ report }) {
  const structured = report.structured || report.structured_report;
  const ocr = report.ocr || {};

  if (!structured) {
    return <div style={{ color: 'var(--status-abnormal)' }}>Incomplete report data</div>;
  }

  const getStatusColor = (status) => {
    switch(status) {
      case 'NORMAL': return 'var(--status-normal)';
      case 'BORDERLINE': return 'var(--status-borderline)';
      case 'ABNORMAL': return 'var(--status-abnormal)';
      case 'CRITICAL': return 'var(--status-critical)';
      default: return 'var(--text-muted)';
    }
  };

  const getStatusBg = (status) => {
    switch(status) {
      case 'NORMAL': return 'var(--status-normal-bg)';
      case 'BORDERLINE': return 'var(--status-borderline-bg)';
      case 'ABNORMAL': return 'var(--status-abnormal-bg)';
      case 'CRITICAL': return 'var(--status-critical-bg)';
      default: return 'rgba(255,255,255,0.05)';
    }
  };

  return (
    <div>
      {/* Urgency Banner */}
      {report.urgency && (
        <motion.div 
          initial={{ scale: 0.95 }}
          animate={{ scale: 1 }}
          style={{ 
            background: 'linear-gradient(135deg, rgba(220,38,38,0.2), rgba(185,28,28,0.1))',
            border: '1.5px solid rgba(239,68,68,0.8)',
            padding: '1.25rem', borderRadius: '12px', marginBottom: '2rem',
            display: 'flex', alignItems: 'center', gap: '1rem',
            boxShadow: '0 4px 20px rgba(239,68,68,0.2)'
          }}
        >
          <AlertTriangle size={32} color="var(--status-critical)" />
          <div>
            <h4 style={{ color: 'var(--status-critical)', margin: 0 }}>CRITICAL VALUES DETECTED</h4>
            <p style={{ margin: '4px 0 0', fontSize: '0.9rem', color: '#fca5a5' }}>Please consult a doctor immediately regarding the critical test results below.</p>
          </div>
        </motion.div>
      )}

      {/* Patient Info */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        <div className="glass-card" style={{ padding: '1.25rem' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Patient</p>
          <p style={{ fontSize: '1.25rem', fontWeight: 600, marginTop: '0.25rem' }}>{structured.patient || 'N/A'}</p>
        </div>
        <div className="glass-card" style={{ padding: '1.25rem' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Date</p>
          <p style={{ fontSize: '1.25rem', fontWeight: 600, marginTop: '0.25rem' }}>{structured.report_date || 'N/A'}</p>
        </div>
        <div className="glass-card" style={{ padding: '1.25rem' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Type</p>
          <p style={{ fontSize: '1.25rem', fontWeight: 600, marginTop: '0.25rem' }}>{structured.report_type || 'N/A'}</p>
        </div>
      </div>

      {/* AI Explanation */}
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={20} color="var(--primary)" /> Plain-Language Explanation
        </h3>
        <div className="glass-card markdown-body" style={{ padding: '1.5rem' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {report.summary || report.explanation || ''}
          </ReactMarkdown>
        </div>
      </div>

      {/* Test Table */}
      <h3 style={{ marginBottom: '1rem' }}>Extracted Tests</h3>
      <div style={{ borderRadius: '12px', border: '1px solid var(--border)', overflow: 'hidden' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1.5fr 1fr', background: 'rgba(255,255,255,0.05)', padding: '12px 16px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>
          <div>Test Name</div>
          <div>Value</div>
          <div>Unit</div>
          <div>Reference Range</div>
          <div>Status</div>
        </div>
        
        {structured.tests?.map((t, idx) => (
          <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1.5fr 1fr', padding: '12px 16px', borderTop: '1px solid var(--border)', alignItems: 'center', background: t.status === 'CRITICAL' ? 'rgba(239, 68, 68, 0.05)' : 'transparent' }}>
            <div style={{ fontWeight: 500, color: 'var(--text-main)' }}>{t.name}</div>
            <div style={{ fontWeight: 600, color: 'var(--primary)' }}>{t.value}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{t.unit}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{t.reference_range}</div>
            <div>
              <span style={{ 
                padding: '4px 10px', 
                borderRadius: '20px', 
                fontSize: '0.75rem', 
                fontWeight: 700,
                background: getStatusBg(t.status),
                color: getStatusColor(t.status),
                border: `1px solid ${getStatusColor(t.status)}`
              }}>
                {t.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
