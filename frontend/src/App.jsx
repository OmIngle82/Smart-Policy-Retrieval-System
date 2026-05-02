/**
 * File: src/App.jsx

 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, History, Plus, MessageSquare, LogOut, Shield, X, Sun, Moon } from 'lucide-react';
import {
  getUserRoles,
  logout,
  fetchChatSessions,
  deleteChatSession
} from './api/client';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';

import { Toaster, toast } from 'react-hot-toast';
import './index.css';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('access_token'));
  const [page, setPage] = useState('landing');
  const [roles, setRoles] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem('app-theme') || 'dark');

  useEffect(() => {
    document.documentElement.className = theme === 'light' ? 'light-theme' : '';
    localStorage.setItem('app-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');


  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      setRoles(getUserRoles());
      setPage('chat');
    }
  }, []);

  useEffect(() => {
    if (page === 'chat') {
      loadSessions();
    }
  }, [page]);

  const loadSessions = async () => {
    try {
      console.log("Fetching chat sessions...");
      const res = await fetchChatSessions();
      console.log("Sessions loaded:", res.data?.length || 0);
      setSessions(res.data || []);
    } catch (err) {
      console.error("Failed to load sessions:", err);
      toast.error("Failed to load chat history: " + err.message);
    }
  };

  const handleLoginSuccess = () => {
    setRoles(getUserRoles());
    setPage('chat');
  };

  const handleLogout = () => {
    logout();
    setRoles([]);
    setPage('landing');
    setCurrentSessionId(null);
  };

  const startNewChat = () => {
    setCurrentSessionId(null);
    setPage('chat');
  };

  const selectSession = (id) => {
    setCurrentSessionId(id);
    setPage('chat');
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteChatSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (currentSessionId === id) setCurrentSessionId(null);
      toast.success('Session deleted');
    } catch {
      toast.error('Failed to delete session');
    }
  };

  if (page === 'landing') {
    return <LandingPage onStart={() => {
      const token = localStorage.getItem('access_token');
      if (token) {
        setRoles(getUserRoles());
        setPage('chat');
      } else {
        setPage('auth');
      }
    }} />;
  }

  if (page === 'auth') {
    return <AuthPage onLoginSuccess={handleLoginSuccess} />;
  }

  const isAdmin = roles.includes('admin');

  return (
    <div className={`chat-layout ${theme === 'light' ? 'light-theme' : ''}`}>
      <Toaster position="top-center" toastOptions={{
        style: { 
          background: theme === 'dark' ? 'rgba(25, 10, 35, 0.9)' : 'rgba(255, 255, 255, 0.9)', 
          color: theme === 'dark' ? '#fff' : '#1a1625', 
          border: theme === 'dark' ? '1px solid rgba(138,43,226,0.3)' : '1px solid rgba(122, 34, 255, 0.2)', 
          backdropFilter: 'blur(10px)' 
        },
        success: { iconTheme: { primary: '#7a22ff', secondary: '#fff' } }
      }} />

      <motion.aside
        initial={{ x: -280 }}
        animate={{ x: 0 }}
        className="chat-sidebar"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem', padding: '0 0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{ background: 'var(--clr-primary)', padding: '0.6rem', borderRadius: '14px', color: '#fff', boxShadow: '0 8px 16px rgba(138, 43, 226, 0.4)' }}>
              <Sparkles size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0, letterSpacing: '-0.8px', color: 'var(--clr-text-main)' }}>PolicyAI</h1>
              <p style={{ fontSize: '0.65rem', color: 'var(--clr-text-muted)', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 700 }}>Portal Hub</p>
            </div>
          </div>
          <button 
            onClick={toggleTheme}
            style={{ 
              background: 'rgba(138, 43, 226, 0.1)', 
              border: '1px solid var(--clr-border)', 
              color: 'var(--clr-primary)',
              width: '38px',
              height: '38px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '2.5rem' }}>
          <button
            className={`session-item ${page === 'chat' && !currentSessionId ? 'active' : ''}`}
            onClick={startNewChat}
            style={{ width: '100%', border: 'none', background: 'transparent' }}
          >
            <Plus size={18} />
            <span>Start New Chat</span>
          </button>

          {isAdmin && (
            <button
              className={`session-item ${page === 'admin' ? 'active' : ''}`}
              onClick={() => setPage('admin')}
              style={{ width: '100%', border: 'none', background: 'transparent' }}
            >
              <Shield size={18} />
              <span>Admin Console</span>
            </button>
          )}


        </div>

        {page === 'chat' && (
          <div className="history-container" style={{ flex: 1, overflowY: 'auto', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1.5rem' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--clr-text-muted)', marginBottom: '1.25rem', paddingLeft: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <History size={12} /> RECENT HISTORY
            </div>
            <div className="history-section">
              <AnimatePresence>
                {sessions.map((s) => (
                  <motion.div
                    key={s.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className={`session-item ${currentSessionId === s.id ? 'active' : ''}`}
                    onClick={() => selectSession(s.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', overflow: 'hidden' }}>
                      <MessageSquare size={16} style={{ color: currentSessionId === s.id ? 'var(--clr-primary)' : 'var(--clr-text-muted)', flexShrink: 0 }} />
                      <span style={{
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        fontWeight: currentSessionId === s.id ? 700 : 500,
                        fontSize: '0.85rem'
                      }}>{s.title}</span>
                    </div>
                    <button
                      className="delete-btn-mini"
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--clr-text-muted)', opacity: 0.5, cursor: 'pointer', display: 'flex', padding: '4px' }}
                    >
                      <X size={14} />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}

        <div style={{ marginTop: 'auto', paddingTop: '1.5rem', borderTop: '1px solid rgba(138,43,226,0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '1.25rem', padding: '0 0.5rem' }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: '14px',
              background: 'linear-gradient(135deg, var(--clr-primary), #3b74ca)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              color: '#fff',
              fontSize: '1.1rem',
              boxShadow: '0 8px 16px rgba(138, 43, 226, 0.3)'
            }}>
              {roles[0]?.[0]?.toUpperCase() || 'U'}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--clr-text-main)', letterSpacing: '-0.3px' }}>Policy Analyst</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--clr-text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.8px' }}>{roles.join(' • ')}</div>
            </div>
          </div>
          <button
            className="session-item"
            style={{
              width: '100%',
              justifyContent: 'center',
              gap: '0.75rem',
              background: 'rgba(255, 23, 68, 0.05)',
              borderColor: 'rgba(255, 23, 68, 0.1)',
              color: 'var(--clr-error)',
              fontWeight: 700
            }}
            onClick={handleLogout}
          >
            <LogOut size={16} />
            <span>Sign Out Access</span>
          </button>
        </div>
      </motion.aside>

      <main className="chat-main">
        <AnimatePresence mode="wait">
          <motion.div
            key={page}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{ height: '100%', width: '100%' }}
          >
            {page === 'chat' && (
              <ChatPage
                roles={roles}
                sessionId={currentSessionId}
                onSessionCreated={loadSessions}
                onSwitchToSession={selectSession}
              />
            )}
            {page === 'admin' && <AdminPage />}
          </motion.div>
        </AnimatePresence>
      </main>


    </div>
  );
}
