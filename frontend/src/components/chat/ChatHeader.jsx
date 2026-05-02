import { MessageSquare, Paperclip, Cpu, Cloud, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ChatHeader({ activeAttachedDocs, inferenceMode, setMode, isFromCache }) {
    return (
        <header className="chat-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(79, 142, 247, 0.1)', padding: '0.4rem', borderRadius: '10px', color: 'var(--clr-primary)' }}>
                    <MessageSquare size={18} />
                </div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Conversational Analysis</h2>

                {activeAttachedDocs && (
                    <motion.div
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        style={{ marginLeft: '1rem', background: 'rgba(138, 43, 226, 0.1)', border: '1px solid var(--clr-primary-glow)', padding: '0.3rem 0.8rem', borderRadius: '20px', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', fontWeight: 600, color: 'var(--clr-text-main)' }}
                    >
                        <Paperclip size={12} color="var(--clr-primary)" />
                        Context: {activeAttachedDocs}
                    </motion.div>
                )}

                {isFromCache && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        style={{ marginLeft: '0.5rem', background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.3)', padding: '0.3rem 0.8rem', borderRadius: '20px', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.7rem', fontWeight: 800, color: '#ffd700' }}
                    >
                        <Zap size={10} fill="#ffd700" />
                        HIGH SPEED CACHE
                    </motion.div>
                )}
            </div>
            <div style={{ display: 'flex', gap: '0.6rem', padding: '4px', background: 'rgba(255,255,255,0.04)', borderRadius: '14px' }}>
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`chip ${inferenceMode === 'local' ? 'active' : ''}`}
                    onClick={() => setMode('local')}
                    style={{ background: inferenceMode === 'local' ? 'var(--clr-primary)' : 'transparent', border: 'none', color: '#fff', padding: '6px 14px', borderRadius: '10px', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', transition: '0.3s' }}
                >
                    <Cpu size={14} /> Local
                </motion.button>
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`chip ${inferenceMode === 'cloud' ? 'active' : ''}`}
                    onClick={() => setMode('cloud')}
                    style={{ background: inferenceMode === 'cloud' ? 'var(--clr-primary)' : 'transparent', border: 'none', color: '#fff', padding: '6px 14px', borderRadius: '10px', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', transition: '0.3s' }}
                >
                    <Cloud size={14} /> Cloud
                </motion.button>
            </div>
        </header>
    );
}
