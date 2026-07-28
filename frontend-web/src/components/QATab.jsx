import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Search, FileText, Database, CornerDownRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function QATab({ backendUrl }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleAsk = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${backendUrl}/qa/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      
      if (!response.ok) throw new Error('Failed to fetch answer');
      const data = await response.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.answer,
        report_chunks: data.report_chunks || [],
        reference_chunks: data.reference_chunks || []
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Sorry, an error occurred while fetching the answer.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const quickQuestions = [
    "What does low hemoglobin mean?",
    "Why is my HbA1c high?",
    "Is my cholesterol dangerous?",
    "What causes low platelets?"
  ];

  return (
    <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 180px)' }}>
      {/* Chat Area */}
      <div style={{ flex: 3, display: 'flex', flexDirection: 'column' }}>
        
        {messages.length === 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>⚡ Quick Questions</p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {quickQuestions.map((q, i) => (
                <button 
                  key={i} 
                  className="btn-secondary" 
                  style={{ fontSize: '0.85rem' }}
                  onClick={() => {
                    setInput(q);
                    setTimeout(() => handleAsk({ preventDefault: () => {} }), 50);
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="glass-card" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1rem' }}>
          {messages.length === 0 ? (
            <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Bot size={48} style={{ opacity: 0.2, margin: '0 auto 1rem' }} />
              <p>Ask a question about your health or uploaded reports.</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ 
                  display: 'flex', 
                  gap: '12px', 
                  alignItems: 'flex-start',
                  background: msg.role === 'user' ? 'rgba(255,255,255,0.02)' : 'var(--primary-bg)',
                  border: `1px solid ${msg.role === 'user' ? 'var(--border)' : 'rgba(0,240,255,0.2)'}`,
                  padding: '1.25rem',
                  borderRadius: '16px'
                }}
              >
                <div style={{ 
                  background: msg.role === 'user' ? 'var(--surface-hover)' : 'var(--primary)',
                  color: msg.role === 'user' ? 'var(--text-muted)' : '#050B14',
                  padding: '8px', borderRadius: '50%', flexShrink: 0 
                }}>
                  {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                </div>
                <div className="markdown-body" style={{ flex: 1 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </motion.div>
            ))
          )}
          
          {isLoading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', gap: '12px', padding: '1.25rem' }}>
              <div style={{ background: 'var(--primary)', color: '#050B14', padding: '8px', borderRadius: '50%', flexShrink: 0 }}>
                <Bot size={20} />
              </div>
              <div style={{ color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}><Search size={16} /></motion.div>
                Analyzing reports & references...
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleAsk} style={{ display: 'flex', gap: '12px' }}>
          <input 
            type="text" 
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type your question here..."
            disabled={isLoading}
            className="glass-card"
            style={{ 
              flex: 1, 
              padding: '1rem 1.5rem', 
              color: 'var(--text-main)', 
              fontSize: '1rem',
              outline: 'none'
            }}
          />
          <button 
            type="submit" 
            className="btn-primary" 
            disabled={!input.trim() || isLoading}
            style={{ padding: '0 1.5rem' }}
          >
            <Send size={20} />
          </button>
        </form>
      </div>

      {/* Retrieval Inspector */}
      <div style={{ flex: 2, display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem' }}>
          <Search size={20} color="var(--primary)" /> Retrieval Inspector
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Shows exact chunks retrieved by the hybrid RAG system for the latest answer.
        </p>

        <div className="glass-card" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {messages.filter(m => m.role === 'assistant').length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '2rem' }}>
              No queries yet. Ask a question to see retrieved sources.
            </div>
          ) : (
            (() => {
              const lastAns = messages.filter(m => m.role === 'assistant').pop();
              return (
                <AnimatePresence>
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} key={messages.length}>
                    
                    <h4 style={{ color: 'var(--primary)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={14} /> Store A: Your Reports
                    </h4>
                    {lastAns?.report_chunks?.length > 0 ? (
                      lastAns.report_chunks.map((chunk, i) => (
                        <div key={i} style={{ background: 'rgba(0, 240, 255, 0.05)', borderLeft: '3px solid var(--primary)', padding: '12px', borderRadius: '0 8px 8px 0', marginBottom: '12px', fontSize: '0.85rem' }}>
                          <div style={{ color: 'var(--primary)', fontWeight: 600, marginBottom: '6px' }}>📋 {chunk.source_name}</div>
                          <div style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{chunk.snippet.substring(0, 200)}...</div>
                          <div style={{ marginTop: '8px', fontSize: '0.75rem', background: 'rgba(255,255,255,0.1)', display: 'inline-block', padding: '2px 8px', borderRadius: '12px' }}>Score: {(chunk.score * 100).toFixed(0)}%</div>
                        </div>
                      ))
                    ) : (
                      <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: '8px', color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '20px', border: '1px dashed var(--border)' }}>No relevant chunks found.</div>
                    )}

                    <h4 style={{ color: 'var(--accent)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px', marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Database size={14} /> Store B: Medical References
                    </h4>
                    {lastAns?.reference_chunks?.length > 0 ? (
                      lastAns.reference_chunks.map((chunk, i) => (
                        <div key={i} style={{ background: 'rgba(112, 0, 255, 0.05)', borderLeft: '3px solid var(--accent)', padding: '12px', borderRadius: '0 8px 8px 0', marginBottom: '12px', fontSize: '0.85rem' }}>
                          <div style={{ color: 'var(--accent)', fontWeight: 600, marginBottom: '6px' }}>📖 {chunk.source_name}</div>
                          <div style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{chunk.snippet.substring(0, 200)}...</div>
                          <div style={{ marginTop: '8px', fontSize: '0.75rem', background: 'rgba(255,255,255,0.1)', display: 'inline-block', padding: '2px 8px', borderRadius: '12px' }}>Score: {(chunk.score * 100).toFixed(0)}%</div>
                        </div>
                      ))
                    ) : (
                      <div style={{ padding: '12px', background: 'var(--surface)', borderRadius: '8px', color: 'var(--text-muted)', fontSize: '0.85rem', border: '1px dashed var(--border)' }}>No relevant chunks found.</div>
                    )}

                  </motion.div>
                </AnimatePresence>
              );
            })()
          )}
        </div>
      </div>
    </div>
  );
}
