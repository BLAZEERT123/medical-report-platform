import React, { useState, useEffect } from 'react';
import { Activity, User as UserIcon, TrendingUp, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea
} from 'recharts';

export default function TrendsTab({ backendUrl }) {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState('');
  const [trendData, setTrendData] = useState(null);
  const [selectedBiomarker, setSelectedBiomarker] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Fetch unique patients on mount
    fetch(`${backendUrl}/reports/patients`)
      .then(res => res.json())
      .then(data => {
        setPatients(data);
        if (data.length > 0) {
          setSelectedPatient(data[0]);
        }
      })
      .catch(err => console.error(err));
  }, [backendUrl]);

  useEffect(() => {
    if (!selectedPatient) return;
    setIsLoading(true);
    fetch(`${backendUrl}/reports/trends/${encodeURIComponent(selectedPatient)}`)
      .then(res => res.json())
      .then(data => {
        setTrendData(data.trends);
        const markers = Object.keys(data.trends);
        if (markers.length > 0) {
          setSelectedBiomarker(markers[0]);
        } else {
          setSelectedBiomarker('');
        }
      })
      .catch(err => console.error(err))
      .finally(() => setIsLoading(false));
  }, [selectedPatient, backendUrl]);

  // Format data for Recharts
  const currentChartData = selectedBiomarker && trendData ? trendData[selectedBiomarker] : [];
  
  // Try to parse reference range for the ReferenceArea (e.g. "13-17" or "<100")
  let yMinRef = null;
  let yMaxRef = null;
  if (currentChartData.length > 0 && currentChartData[0].reference_range) {
    const range = currentChartData[0].reference_range;
    const dashMatch = range.match(/([\d\.]+)\s*-\s*([\d\.]+)/);
    if (dashMatch) {
      yMinRef = parseFloat(dashMatch[1]);
      yMaxRef = parseFloat(dashMatch[2]);
    } else if (range.includes('<')) {
      yMaxRef = parseFloat(range.replace(/[^\d\.]/g, ''));
    } else if (range.includes('>')) {
      yMinRef = parseFloat(range.replace(/[^\d\.]/g, ''));
    }
  }

  // Custom Tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="glass-card" style={{ padding: '1rem', border: '1px solid var(--border)' }}>
          <p style={{ color: 'var(--primary)', fontWeight: 600, marginBottom: '0.5rem' }}>{label}</p>
          <p style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
            {data.value} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{data.unit}</span>
          </p>
          <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', 
            color: data.status === 'NORMAL' ? 'var(--status-normal)' : 'var(--status-abnormal)',
            textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700
          }}>
            {data.status}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 180px)' }}>
      {/* Sidebar Controls */}
      <div style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserIcon size={18} color="var(--primary)" /> Select Patient
          </h3>
          <select 
            value={selectedPatient} 
            onChange={(e) => setSelectedPatient(e.target.value)}
            style={{ 
              width: '100%', padding: '0.75rem', borderRadius: '8px', 
              background: 'rgba(0,0,0,0.3)', color: 'var(--text-main)', 
              border: '1px solid var(--border)', outline: 'none'
            }}
          >
            {patients.length === 0 && <option value="">No patients found</option>}
            {patients.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        <div className="glass-card" style={{ padding: '1.5rem', flex: 1, overflowY: 'auto' }}>
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} color="var(--accent)" /> Biomarkers
          </h3>
          {isLoading ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading trends...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {trendData && Object.keys(trendData).length > 0 ? (
                Object.keys(trendData).map(marker => (
                  <button
                    key={marker}
                    onClick={() => setSelectedBiomarker(marker)}
                    style={{
                      padding: '0.75rem 1rem',
                      textAlign: 'left',
                      background: selectedBiomarker === marker ? 'var(--primary-bg)' : 'transparent',
                      color: selectedBiomarker === marker ? 'var(--primary)' : 'var(--text-main)',
                      border: `1px solid ${selectedBiomarker === marker ? 'rgba(0, 240, 255, 0.2)' : 'transparent'}`,
                      borderRadius: '8px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      fontWeight: selectedBiomarker === marker ? 600 : 400
                    }}
                  >
                    {marker}
                  </button>
                ))
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No data available for this patient.</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chart Area */}
      <div className="glass-card" style={{ flex: 1, padding: '2rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1.5rem' }}>
            <TrendingUp size={24} color="var(--primary)" /> 
            {selectedBiomarker || 'Select a biomarker'} Trend
          </h2>
          {selectedBiomarker && trendData && trendData[selectedBiomarker] && (
            <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontSize: '0.9rem' }}>
              Showing {trendData[selectedBiomarker].length} data point(s) for {selectedPatient}. 
              {yMinRef !== null || yMaxRef !== null ? ` Reference Range: ${trendData[selectedBiomarker][0].reference_range}` : ''}
            </p>
          )}
        </div>

        <div style={{ flex: 1, minHeight: 0 }}>
          {currentChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={currentChartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey="date" 
                  stroke="var(--text-muted)" 
                  tick={{ fill: 'var(--text-muted)' }} 
                  tickMargin={10} 
                />
                <YAxis 
                  stroke="var(--text-muted)" 
                  tick={{ fill: 'var(--text-muted)' }} 
                  tickMargin={10}
                  domain={['auto', 'auto']}
                />
                <Tooltip content={<CustomTooltip />} />
                
                {/* Reference Range Highlight Area */}
                {(yMinRef !== null || yMaxRef !== null) && (
                  <ReferenceArea 
                    y1={yMinRef !== null ? yMinRef : undefined} 
                    y2={yMaxRef !== null ? yMaxRef : undefined} 
                    fill="var(--status-normal-bg)" 
                    fillOpacity={0.5} 
                    strokeOpacity={0}
                  />
                )}
                
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="var(--primary)" 
                  strokeWidth={3}
                  dot={{ fill: 'var(--bg-color)', stroke: 'var(--primary)', strokeWidth: 2, r: 6 }}
                  activeDot={{ r: 8, fill: 'var(--primary)', stroke: '#fff', strokeWidth: 2 }}
                  animationDuration={1500}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              <div style={{ textAlign: 'center' }}>
                <AlertCircle size={48} style={{ opacity: 0.2, margin: '0 auto 1rem' }} />
                <p>No data to display. Please select a patient and biomarker.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
