import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Paperclip, Send } from 'lucide-react';
import {
    queryPolicy,
    uploadFromChat,
    fetchSessionHistory,
    createChatSession
} from '../api/client';
import { toast } from 'react-hot-toast';

// Modular Components
import ChatHeader from '../components/chat/ChatHeader';
import MessageList from '../components/chat/MessageList';
import EvidencePanel from '../components/chat/EvidencePanel';

export default function ChatPage({ roles, sessionId, onSessionCreated, onSwitchToSession }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [inferenceMode, setMode] = useState('local');
    const [activeCitation, setCitation] = useState(null);
    const [uploadProgress, setUploadProgress] = useState(0);

    const [isFromCache, setIsFromCache] = useState(false);
    const scrollRef = useRef(null);
    const textareaRef = useRef(null);
    const fileInputRef = useRef(null);

    const [pdfWidth, setPdfWidth] = useState(480);
    const isResizing = useRef(false);

    // ── Resizing Logic ────────────────────────────────────────────────────────
    const startResizing = (e) => {
        e.preventDefault();
        isResizing.current = true;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', stopResizing);
        document.body.classList.add('resizing');
    };

    const stopResizing = () => {
        isResizing.current = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', stopResizing);
        document.body.classList.remove('resizing');
    };

    const handleMouseMove = (e) => {
        if (!isResizing.current) return;
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 320 && newWidth < window.innerWidth * 0.7) {
            setPdfWidth(newWidth);
        }
    };

    // ── Data Sync Logic ───────────────────────────────────────────────────────
    useEffect(() => {
        if (sessionId) {
            loadHistory(sessionId);
        } else {
            // When sessionId is null (new chat), clear messages unless there are status/uploading messages
            setMessages(prev => prev.some(m => m.isStatus || m.isUploading) ? prev : []);
            setIsFromCache(false); // Reset cache status for new sessions
        }
    }, [sessionId]);

    const activeAttachedDocs = useMemo(() => {
        const readyMsgs = messages.filter(m => m.text && m.text.includes('✅ System Ready:'));
        if (readyMsgs.length === 0) return null;
        const lastMsg = readyMsgs[readyMsgs.length - 1].text;
        const match = lastMsg.match(/'([^']+)'/);
        return match ? match[1] : null;
    }, [messages]);

    const loadHistory = async (id) => {
        setLoading(true);
        try {
            const res = await fetchSessionHistory(id);
            const historyMsgs = res.data.map(m => ({
                role: m.role,
                text: m.content,
                citations: m.citations || [],
                query: m.query || ''
            }));

            setMessages(prev => {
                const localStatus = prev.filter(m => m.isStatus || m.isUploading);
                return [...historyMsgs, ...localStatus];
            });
            setIsFromCache(res.is_from_cache || false); // Assuming res might contain this info
        } catch (err) {
            console.error("History Error:", err);
        } finally {
            setLoading(false);
        }
    };

    async function sendMessage(text) {
        const question = text || input.trim();
        if (!question || loading) return;

        let activeId = sessionId;
        if (!activeId) {
            try {
                const res = await createChatSession(question.slice(0, 30));
                activeId = res.session_id;
                onSessionCreated();
                onSwitchToSession(activeId);
            } catch (err) { console.error(err); }
        }

        const userMsg = { role: 'user', text: question };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const data = await queryPolicy(question, inferenceMode, messages.map(m => ({ role: m.role, content: m.text })), activeId);
            setMessages(prev => [...prev, {
                role: 'bot',
                text: data?.answer || "I'm sorry, I couldn't generate an answer.",
                citations: data?.citations || [],
                query: question,
                isNew: true
            }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'bot', text: `⚠️ Error: ${err.message}` }]);
        } finally { setLoading(false); }
    }

    async function handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        let activeId = sessionId;
        if (!activeId) {
            try {
                const cleanName = file.name.replace(/\.[^/.]+$/, "");
                const res = await createChatSession(cleanName.length > 25 ? cleanName.substring(0, 25) + '...' : cleanName);
                activeId = res.session_id;
                onSessionCreated();
                onSwitchToSession(activeId);
            } catch (err) {
                toast.error("Failed to initialize session: " + err.message);
                return;
            }
        }

        const statusId = Date.now();
        setUploadProgress(0);
        setMessages(prev => [...prev, { id: statusId, role: 'bot', text: `⏳ Ingesting '${file.name}'...`, isStatus: true, isUploading: true }]);

        try {
            await uploadFromChat(file, file.name, activeId, (pct) => setUploadProgress(pct));
            setMessages(prev => prev.map(m => m.id === statusId ? { ...m, isUploading: false, text: `⚙️ Vector Core: Indexing '${file.name}'...` } : m));
            setTimeout(() => {
                setMessages(prev => prev.map(m => m.id === statusId ? { ...m, isStatus: false, text: `✅ System Ready: '${file.name}' indexed.` } : m));
                onSessionCreated();
            }, 2000);
        } catch (err) {
            setMessages(prev => prev.map(m => m.id === statusId ? { ...m, text: `❌ Failed: ${err.message}`, isStatus: false, isUploading: false } : m));
        }
        e.target.value = '';
    }

    // Spring optimized for structural layout changes
    const layoutSpring = { type: "spring", stiffness: 300, damping: 32, mass: 0.8 };

    return (
        <div
            className="workspace-layout"
            style={{ '--pdf-width': `${pdfWidth}px` }}
        >
            <motion.main
                className="chat-split-content"
                style={{
                    flex: '1 1 auto',
                    minWidth: 0,
                    position: 'relative',
                    zIndex: 1,
                    pointerEvents: 'auto'
                }}
            >
                <ChatHeader
                    activeAttachedDocs={activeAttachedDocs}
                    inferenceMode={inferenceMode}
                    setMode={setMode}
                    isFromCache={isFromCache}
                />

                <MessageList
                    messages={messages}
                    loading={loading}
                    setCitation={setCitation}
                    uploadProgress={uploadProgress}
                    chatEndRef={scrollRef}
                    sendMessage={sendMessage}
                />

                <div className="chat-input-container">
                    <motion.div initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="input-box">
                        <button className="paperclip-btn" onClick={() => fileInputRef.current.click()} title="Attach Policy PDF">
                            <Paperclip size={20} />
                        </button>
                        <input type="file" ref={fileInputRef} hidden accept=".pdf" onChange={handleFileUpload} />
                        <textarea
                            ref={textareaRef}
                            placeholder="Message PolicyAI..."
                            value={input}
                            onChange={(e) => {
                                setInput(e.target.value);
                                e.target.style.height = 'auto';
                                e.target.style.height = e.target.scrollHeight + 'px';
                            }}
                            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
                            rows={1}
                        />
                        <button
                            className={`send-btn ${input.trim() ? 'active' : ''}`}
                            onClick={() => sendMessage()}
                            disabled={loading || !input.trim()}
                            title="Send Message"
                        >
                            <Send size={18} />
                        </button>
                    </motion.div>
                </div>
            </motion.main>

            <AnimatePresence>
                {activeCitation && (
                    <motion.div
                        key="evidence-container"
                        style={{
                            display: 'flex',
                            height: '100%',
                            overflow: 'hidden',
                            zIndex: 100,
                            flexShrink: 0
                        }}
                        initial={{ width: '0px', opacity: 0 }}
                        animate={{ width: `${pdfWidth}px`, opacity: 1 }}
                        exit={{ width: '0px', opacity: 0 }}
                        transition={layoutSpring}
                    >
                        {/* Internal wrapper for content to prevent compression while shrinking */}
                        <div style={{ minWidth: `${pdfWidth}px`, height: '100%', display: 'flex' }}>
                            <div className={`resizer-bar ${isResizing.current ? 'active' : ''}`} onMouseDown={startResizing} />
                            <EvidencePanel
                                activeCitation={activeCitation}
                                setCitation={setCitation}
                                pdfWidth={pdfWidth - 6}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
