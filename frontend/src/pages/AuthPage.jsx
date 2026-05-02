/**
 * File: src/pages/AuthPage.jsx

 * 
 * Features:
 *   - Premium Glassmorphism V2 design with 24px blur.
 *   - Lucide iconography for form inputs.
 *   - Performance-optimized form handling.
 *   - High-fidelity visual branding.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Shield,
    User,
    Lock,
    Mail,
    ArrowRight,
    Sparkles
} from 'lucide-react';
import { login, register } from '../api/client';

export default function AuthPage({ onLoginSuccess }) {
    const [mode, setMode] = useState('login');
    const [form, setForm] = useState({ username: '', email: '', password: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
        setError('');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            if (mode === 'login') {
                await login(form.username, form.password);
                onLoginSuccess();
            } else {
                await register(form.username, form.email, form.password);
                await login(form.username, form.password);
                onLoginSuccess();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page" style={{
            height: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'radial-gradient(circle at 2% 2%, rgba(138, 43, 226, 0.2) 0%, transparent 45%), radial-gradient(circle at 98% 98%, rgba(0, 240, 255, 0.15) 0%, transparent 45%)'
        }}>
            <motion.div
                initial={{ opacity: 0, scale: 0.98, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                className="glass-panel"
                style={{ width: '100%', maxWidth: '440px', padding: '3rem', borderRadius: '32px', border: '1px solid var(--clr-primary-glow)' }}
            >
                <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
                    <div style={{
                        width: 70, height: 70, background: 'linear-gradient(135deg, var(--clr-primary), #00f0ff)',
                        borderRadius: '20px', display: 'flex', alignItems: 'center',
                        justifyContent: 'center', margin: '0 auto 1.5rem', color: '#fff',
                        boxShadow: '0 12px 30px var(--clr-primary-glow)'
                    }}>
                        <Shield size={36} />
                    </div>
                    <h2 style={{ fontSize: '2rem', fontWeight: 800, margin: 0, letterSpacing: '-0.8px' }}>PolicyAI</h2>
                    <p style={{ color: 'var(--clr-text-muted)', fontSize: '0.9rem', marginTop: '0.6rem', fontWeight: 500 }}>Intelligent Policy Retrieval Portal</p>
                </div>

                <AnimatePresence mode="wait">
                    <motion.div
                        key={error}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: error ? 1 : 0, height: error ? 'auto' : 0 }}
                    >
                        {error && (
                            <div style={{ background: 'rgba(255, 23, 68, 0.1)', color: 'var(--clr-error)', padding: '0.85rem 1.25rem', borderRadius: '14px', marginBottom: '1.5rem', border: '1px solid rgba(255, 23, 68, 0.2)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Sparkles size={14} /> {error}
                            </div>
                        )}
                    </motion.div>
                </AnimatePresence>

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.6rem', fontSize: '0.85rem', fontWeight: 700, color: '#fff', opacity: 0.8 }}>Username</label>
                        <div style={{ position: 'relative' }}>
                            <User size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--clr-text-muted)' }} />
                            <input
                                name="username" type="text" required
                                placeholder="analyst_id"
                                value={form.username} onChange={handleChange}
                                style={{ width: '100%', padding: '0.85rem 1rem 0.85rem 3rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--clr-border)', borderRadius: '16px', color: '#fff', outline: 'none', transition: '0.3s' }}
                            />
                        </div>
                    </div>

                    {mode === 'register' && (
                        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.6rem', fontSize: '0.85rem', fontWeight: 700, color: '#fff', opacity: 0.8 }}>Email Address</label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--clr-text-muted)' }} />
                                <input
                                    name="email" type="email" required
                                    placeholder="name@ministry.gov"
                                    value={form.email} onChange={handleChange}
                                    style={{ width: '100%', padding: '0.85rem 1rem 0.85rem 3rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--clr-border)', borderRadius: '16px', color: '#fff', outline: 'none' }}
                                />
                            </div>
                        </motion.div>
                    )}

                    <div style={{ marginBottom: '2.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.6rem', fontSize: '0.85rem', fontWeight: 700, color: '#fff', opacity: 0.8 }}>Security Password</label>
                        <div style={{ position: 'relative' }}>
                            <Lock size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--clr-text-muted)' }} />
                            <input
                                name="password" type="password" required
                                placeholder="••••••••"
                                value={form.password} onChange={handleChange}
                                style={{ width: '100%', padding: '0.85rem 1rem 0.85rem 3rem', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--clr-border)', borderRadius: '16px', color: '#fff', outline: 'none' }}
                            />
                        </div>
                    </div>

                    <button
                        type="submit" disabled={loading}
                        className="new-chat-btn"
                        style={{ width: '100%', marginBottom: '1.75rem', borderRadius: '16px', padding: '1rem', background: 'linear-gradient(135deg, var(--clr-primary), #00f0ff)', border: 'none', color: '#fff', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', boxShadow: '0 8px 25px var(--clr-primary-glow)', transition: '0.3s' }}
                    >
                        {loading ? 'Authenticating...' : mode === 'login' ? 'Proceed to Chat' : 'Create Secure Profile'}
                        {!loading && <ArrowRight size={20} />}
                    </button>
                </form>

                <div style={{ textAlign: 'center', fontSize: '0.9rem', color: 'var(--clr-text-muted)' }}>
                    {mode === 'login' ? (
                        <>Need internal access? <span onClick={() => setMode('register')} style={{ color: 'var(--clr-primary)', cursor: 'pointer', fontWeight: 700 }}>Register profile</span></>
                    ) : (
                        <>Already registered? <span onClick={() => setMode('login')} style={{ color: 'var(--clr-primary)', cursor: 'pointer', fontWeight: 700 }}>Log In instead</span></>
                    )}
                </div>

                <div style={{ marginTop: '3rem', paddingTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.6rem', color: 'var(--clr-text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1.5px', fontWeight: 600 }}>
                        <Shield size={14} /> Hybrid Security Protocol Active
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
