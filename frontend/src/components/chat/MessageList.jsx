import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, FileText, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ProgressBar from './ProgressBar';

// ── Typing Effect Component ──────────────────────────────────────────────────
function TypingMessage({ text }) {
    const [displayedText, setDisplayedText] = useState('');
    const [index, setIndex] = useState(0);

    useEffect(() => {
        if (index < text.length) {
            const timeout = setTimeout(() => {
                setDisplayedText(prev => prev + text[index]);
                setIndex(prev => prev + 1);
            }, 8);
            return () => clearTimeout(timeout);
        }
    }, [index, text]);

    return (
        <div className="markdown-body">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ node, ...props }) => <b style={{ color: 'var(--clr-primary)' }}>{props.children}</b>
                }}
            >
                {displayedText}
            </ReactMarkdown>
        </div>
    );
}

// ── Keyword Highlighter ──────────────────────────────────────────────────────
function HighlightText({ text, query }) {
    if (!query || typeof query !== 'string') return <span>{text || ""}</span>;
    if (!text || typeof text !== 'string') return <span>{text || ""}</span>;

    const keywords = useMemo(() => {
        try {
            const stopWords = new Set(["what", "is", "the", "a", "an", "for", "in", "of", "and", "to", "how", "do", "does", "explain", "summarize"]);
            return query.toLowerCase().split(/\s+/).filter(w => w && w.length > 2 && !stopWords.has(w));
        } catch (e) {
            console.error("Highlight Calculation Error:", e);
            return [];
        }
    }, [query]);

    if (keywords.length === 0) return <span>{text}</span>;

    const regex = useMemo(() => {
        try {
            return new RegExp(`(${keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
        } catch (e) {
            return null;
        }
    }, [keywords]);

    if (!regex) return <span>{text}</span>;
    const parts = text.split(regex);

    return (
        <span>
            {parts.map((part, i) => regex.test(part) ?
                <mark key={i} style={{ background: 'rgba(79, 142, 247, 0.25)', color: '#fff', borderRadius: '4px', padding: '0 4px' }}>{part}</mark>
                : part)}
        </span>
    );
}

export default function MessageList({ messages, loading, sendMessage, setCitation, uploadProgress, chatEndRef }) {
    return (
        <div className="messages-area" id="msg-area">
            {messages.length === 0 ? (
                <div className="welcome-container">
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                        <div style={{ fontSize: '3.5rem', marginBottom: '1.5rem' }}>🏛️</div>
                        <h1 className="welcome-title">How can I assist your research?</h1>
                        <p style={{ color: 'var(--clr-text-muted)', fontSize: '1rem', marginBottom: '2.5rem' }}>Query Ministry policies, scholarship rules, and legal gazettes with precision.</p>

                        <div className="suggestion-grid">
                            {[
                                "UGC Scholarship eligibility criteria",
                                "Faculty promotion rules 2024",
                                "Study leave application process",
                                "Latest gazette notifications"
                            ].map((s, i) => (
                                <motion.div key={i} whileHover={{ y: -4 }} className="suggestion-chip" onClick={() => sendMessage(s)}>
                                    <Sparkles size={14} color="var(--clr-primary)" /> {s}
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                </div>
            ) : (
                messages.map((msg, i) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ type: "spring", stiffness: 400, damping: 35 }}
                        className={`message ${msg.role}`}
                    >
                        <div className={`message-bubble ${msg.isStatus ? 'status-msg' : ''}`}>
                            {msg.isStatus && <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.6rem' }}><Loader2 size={16} className="animate-spin" /> {msg.text}</div>}
                            {!msg.isStatus && (
                                msg.role === 'bot' ? (
                                    msg.isNew ? <TypingMessage text={msg.text} /> : (
                                        <div className="markdown-body">
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                components={{
                                                    a: ({ node, ...props }) => <b style={{ color: 'var(--clr-primary)' }}>{props.children}</b>
                                                }}
                                            >
                                                {msg.text}
                                            </ReactMarkdown>
                                        </div>
                                    )
                                ) : (
                                    msg.text
                                )
                            )}

                            {msg.isUploading && <ProgressBar progress={uploadProgress} />}

                            {msg.citations?.length > 0 && (
                                <div className="citations-list">
                                    {msg.citations.map((c, ci) => (
                                        <motion.button
                                            key={ci}
                                            whileHover={{ scale: 1.05, y: -2 }}
                                            whileTap={{ scale: 0.95 }}
                                            className="citation-pill"
                                            onClick={() => {
                                                console.log("Citation Clicked:", c);
                                                setCitation({ ...c, query: msg.query || "" });
                                            }}
                                        >
                                            <FileText size={12} /> {c.document_name} · p.{c.page_number}
                                        </motion.button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                ))
            )}
            {loading && (
                <div className="message bot">
                    <div className="message-bubble" style={{ scale: 0.8, alignSelf: 'flex-start', display: 'flex', gap: '6px', padding: '1rem' }}>
                        <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 1 }} style={{ width: 6, height: 6, background: 'var(--clr-primary)', borderRadius: '50%' }} />
                        <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} style={{ width: 6, height: 6, background: 'var(--clr-primary)', borderRadius: '50%' }} />
                        <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} style={{ width: 6, height: 6, background: 'var(--clr-primary)', borderRadius: '50%' }} />
                    </div>
                </div>
            )}
            <div ref={chatEndRef} />
        </div>
    );
}
