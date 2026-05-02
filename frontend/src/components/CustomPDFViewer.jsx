import { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import { searchPlugin } from '@react-pdf-viewer/search';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import { FileText, Sparkles, Maximize2, Minimize2 } from 'lucide-react';

// Import core styles
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/search/lib/styles/index.css';
import '@react-pdf-viewer/page-navigation/lib/styles/index.css';

export default function CustomPDFViewer({ documentName, pageNumber, searchClause }) {
    const [maximized, setMaximized] = useState(false);

    // Initialize Minimalist Plugins
    const searchPluginInstance = searchPlugin();
    const pageNavigationPluginInstance = pageNavigationPlugin();

    const { highlight } = searchPluginInstance;
    const { jumpToPage } = pageNavigationPluginInstance;

    const fileUrl = useMemo(() => {
        if (!documentName) return "";
        return `http://localhost:8000/api/v1/pdf/${documentName}?token=${localStorage.getItem('access_token')}`;
    }, [documentName]);

    // Precision-SLF (Sentence-Level Fragmentation) with Fuzzy Boundary Anchoring
    const searchTerms = useMemo(() => {
        if (typeof searchClause !== 'string' || !searchClause.trim()) return [];

        const clean = searchClause.replace(/\s+/g, ' ').replace(/\[.*?\]/g, '').trim();
        if (clean.length < 8) return [];

        // Split into logical sentences
        // Note: Capturing groups in split() include matches in the result array, which might be undefined
        const sentences = clean.split(/[.!?](\s+|$)/)
            .filter(s => typeof s === 'string')
            .map(s => s.trim())
            .filter(s => s.length > 12);

        const terms = [];
        sentences.forEach(s => {
            terms.push(s);
            const words = s.split(' ');
            if (words && words.length > 10) {
                // Fragment for robustness (especially for line breaks)
                terms.push(words.slice(0, 6).join(' '));
                terms.push(words.slice(-6).join(' '));
                if (words.length > 20) {
                    terms.push(words.slice(Math.floor(words.length / 2) - 3, Math.floor(words.length / 2) + 3).join(' '));
                }
            }
        });

        // Add pattern-based anchors (Steps, Roles, Labels)
        const pattern = /(Step \d+|Role \d+|Instruction|Goal|Responsibility|Task)/gi;
        let match;
        while ((match = pattern.exec(clean)) !== null) {
            if (match[0]) terms.push(match[0]);
        }

        return Array.from(new Set(terms.filter(t => t && typeof t === 'string' && t.length > 3)));
    }, [searchClause]);

    const lastNavigated = useRef({ doc: "", page: -1 });
    const lastHighlighted = useRef("");

    // Keyboard Accessibility: Exit full-screen on Escape
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && maximized) setMaximized(false);
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [maximized]);

    // Resilient Navigation
    useEffect(() => {
        const isNewTarget = lastNavigated.current.doc !== documentName || lastNavigated.current.page !== pageNumber;
        if (typeof jumpToPage === 'function' && pageNumber && isNewTarget) {
            lastNavigated.current = { doc: documentName, page: pageNumber };
            const jumps = [500, 1500, 3000, 5000];
            const timers = jumps.map(ms => setTimeout(() => {
                try { jumpToPage(pageNumber - 1); } catch (e) { }
            }, ms));
            return () => timers.forEach(clearTimeout);
        }
    }, [pageNumber, jumpToPage, documentName]);

    // Premium Highlighting with Neon-Tube Glow
    useEffect(() => {
        const keywordKey = (searchTerms || []).join('|');
        if (searchTerms?.length > 0 && typeof highlight === 'function' && lastHighlighted.current !== keywordKey) {
            lastHighlighted.current = keywordKey;
            const timer = setTimeout(() => {
                try {
                    highlight(searchTerms);
                } catch (e) { }
            }, 800);
            return () => clearTimeout(timer);
        }
    }, [searchTerms, highlight]);

    const ViewerContent = (
        <div className={maximized ? "fullscreen-overlay" : "minimal-pdf-container"} style={maximized ? {} : { height: '100%', width: '100%' }}>
            {/* Minimalist Glass Header */}
            <div className="viewer-glass-header" style={maximized ? { top: '2rem', width: 'auto', minWidth: '450px' } : {}}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                    <div style={{ background: 'var(--clr-primary)', padding: '4px', borderRadius: '6px' }}>
                        <FileText size={14} color="#fff" />
                    </div>
                    <span className="viewer-doc-title" style={maximized ? { fontSize: '0.85rem' } : {}}>{documentName}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div className="viewer-page-indicator">
                        ANALYSIS PAGE {pageNumber || 1}
                    </div>
                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />
                    <button
                        onClick={() => setMaximized(!maximized)}
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer', display: 'flex', transition: '0.2s', padding: '6px', borderRadius: '8px' }}
                        title={maximized ? "Restore (Esc)" : "Full-Screen Focus"}
                    >
                        {maximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </button>
                    <Sparkles size={14} color="#ffd700" className="animate-pulse" />
                </div>
            </div>

            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                <div style={{
                    height: '100%',
                    width: '100%',
                    padding: maximized ? '6rem 15%' : '2.8rem 1rem',
                    display: 'flex',
                    justifyContent: 'center',
                    overflowY: 'auto',
                    background: maximized ? 'var(--clr-bg-main)' : 'transparent'
                }}>
                    <div style={{ width: '100%', maxWidth: maximized ? '1100px' : 'none', boxShadow: maximized ? '0 30px 100px rgba(0,0,0,0.8)' : 'none' }}>
                        <Viewer
                            fileUrl={fileUrl}
                            initialPage={Math.max(0, (pageNumber || 1) - 1)}
                            plugins={[searchPluginInstance, pageNavigationPluginInstance]}
                            theme="dark"
                        />
                    </div>
                </div>
            </Worker>
        </div>
    );

    if (maximized) {
        return createPortal(ViewerContent, document.body);
    }

    return ViewerContent;
}
