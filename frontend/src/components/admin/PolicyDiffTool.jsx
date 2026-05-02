import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitCompare, Layout, FileText, Sparkles, Loader2, AlertCircle } from 'lucide-react';
import { diffDocuments } from '../../api/client';
import ReactMarkdown from 'react-markdown';

export default function PolicyDiffTool({ documents }) {
    const [docA, setDocA] = useState('');
    const [docB, setDocB] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleDiff = async () => {
        if (!docA || !docB) return;
        setLoading(true);
        setError(null);
        try {
            const data = await diffDocuments(docA, docB);
            setResult(data.data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="diff-tool-container">
            <div className="diff-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div className="diff-icon-box">
                        <GitCompare size={20} />
                    </div>
                    <div>
                        <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Policy Version Auditor</h2>
                        <p style={{ fontSize: '0.7rem', color: 'var(--clr-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Comparative AI Analysis</p>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <div className="trust-badge">
                        <Sparkles size={10} /> 98% PRECISION
                    </div>
                </div>
            </div>

            <div className="diff-selection-grid">
                <div className="selection-item">
                    <label>Base Document (V1)</label>
                    <select value={docA} onChange={(e) => setDocA(e.target.value)}>
                        <option value="">Select Document...</option>
                        {documents.map(d => (
                            <option key={d.id} value={d.id}>{d.display_name}</option>
                        ))}
                    </select>
                </div>

                <div className="diff-arrow">
                    <Layout size={18} />
                </div>

                <div className="selection-item">
                    <label>New Version (V2)</label>
                    <select value={docB} onChange={(e) => setDocB(e.target.value)}>
                        <option value="">Select Document...</option>
                        {documents.map(d => (
                            <option key={d.id} value={d.id}>{d.display_name}</option>
                        ))}
                    </select>
                </div>
            </div>

            <button
                className={`diff-action-btn ${(!docA || !docB || loading) ? 'disabled' : ''}`}
                onClick={handleDiff}
                disabled={!docA || !docB || loading}
            >
                {loading ? <Loader2 size={18} className="animate-spin" /> : <GitCompare size={18} />}
                <span>{loading ? 'Analyzing Differences...' : 'Run Version Comparison'}</span>
            </button>

            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="diff-error-box"
                    >
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </motion.div>
                )}

                {result && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="diff-results-area"
                    >
                        <div className="results-header">
                            <FileText size={16} />
                            <span>Analysis: {result.doc_a} vs {result.doc_b}</span>
                        </div>
                        <div className="markdown-body diff-content">
                            <ReactMarkdown>{result.analysis}</ReactMarkdown>
                        </div>
                    </motion.div>
                )}

                {!result && !loading && !error && (
                    <motion.div className="diff-placeholder">
                        <div className="placeholder-icon"><Layout size={40} /></div>
                        <p>Select two policy versions to generate a summarized AI delta report.</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
