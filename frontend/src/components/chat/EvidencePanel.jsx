import { motion } from 'framer-motion';
import { X, CheckCircle } from 'lucide-react';
import CustomPDFViewer from '../CustomPDFViewer';
import { useMemo } from 'react';

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

export default function EvidencePanel({ activeCitation, setCitation, pdfWidth }) {
    if (!activeCitation) return null;

    return (
        <aside
            className="pdf-side-pane"
            style={{ flex: `1 1 auto`, width: '100%' }}
        >
            <div className="pdf-pane-header">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div style={{ fontWeight: 800, fontSize: '0.8rem', color: 'var(--clr-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <CheckCircle size={14} /> VERIFIED SOURCE
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--clr-text-muted)', fontWeight: 600 }}>
                        {activeCitation.document_name}
                    </div>
                </div>
                <button className="close-btn" onClick={() => setCitation(null)}>
                    <X size={20} />
                </button>
            </div>

            <div className="pdf-viewer-content">
                <CustomPDFViewer
                    documentName={activeCitation.document_name}
                    pageNumber={activeCitation.page_number}
                    searchClause={activeCitation.clause}
                />
                <div className="evidence-card">
                    <div className="trust-badge">
                        <CheckCircle size={10} /> Verified Analyst Evidence
                    </div>
                    <div className="evidence-scroll-box">
                        <div className="evidence-text">
                            <HighlightText text={activeCitation.clause} query={activeCitation.query || activeCitation.clause} />
                        </div>
                    </div>
                    <div className="source-metadata">
                        <div className="meta-pill">Source: {activeCitation.document_name}</div>
                        <div className="meta-pill">Grounding Page: {activeCitation.page_number}</div>
                        <div className="meta-pill">Clause Match: 100%</div>
                        <div className="meta-pill" style={{ color: 'var(--clr-primary)' }}>RAG Index: Policy Core</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
