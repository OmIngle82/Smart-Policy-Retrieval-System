/**
 * File: src/pages/AdminPage.jsx

 * 
 * Features:
 *   - User Role Management: Promote/Demote users (Admin, Analyst, Public).
 *   - Document Deletion: Remove indexed policies from the retrieval system.
 *   - PDF Upload: Background ingestion with Real-time Progress Tracking.
 *   - System Health: Quick refresh for data synchronization.
 */

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import {
    Shield,
    Users,
    UploadCloud,
    RefreshCw,
    Trash2,
    UserPlus,
    FileText,
    Activity,
    Lock,
    CheckCircle,
    Info,
    Loader2,
    GitCompare
} from 'lucide-react';
import PolicyDiffTool from '../components/admin/PolicyDiffTool';
import {
    uploadDocument,
    fetchDocuments,
    deleteDocument,
    fetchUsers,
    updateUserRole
} from '../api/client';

export default function AdminPage() {
    const [docs, setDocs] = useState([]);
    const [users, setUsers] = useState([]);
    const [isDragOver, setDragOver] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [loadingDocs, setLoadingDocs] = useState(true);
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const fileInputRef = useRef(null);

    useEffect(() => {
        loadDocs();
        loadUsers();
    }, []);

    async function loadDocs() {
        setLoadingDocs(true);
        try {
            const result = await fetchDocuments();
            setDocs(result.data || []);
        } catch (err) {
            setError('Failed to load document list.');
        } finally {
            setLoadingDocs(false);
        }
    }

    async function loadUsers() {
        setLoadingUsers(true);
        try {
            const result = await fetchUsers();
            setUsers(result.data || []);
        } catch (err) {
            console.error('Failed to load users:', err);
        } finally {
            setLoadingUsers(false);
        }
    }

    async function handleDeleteDoc(id) {
        if (!window.confirm("Remove this document from the search index?")) return;
        try {
            await deleteDocument(id);
            setMessage("✅ Document removed successfully.");
            loadDocs();
        } catch (err) {
            toast.error('Failed to eliminate document permanently.');
        }
    };

    async function handleRoleChange(userId, newRole) {
        try {
            await updateUserRole(userId, newRole);
            setMessage(`✅ ${newRole.toUpperCase()} privilege granted.`);
            loadUsers();
        } catch (err) { toast.error("Failed to update role."); }
    }

    async function performUpload(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) { setError('⚠️ PDF files only.'); return; }
        setUploading(true);
        setUploadProgress(0);
        setMessage('');
        setError('');

        try {
            const displayName = file.name.replace(/\.pdf$/i, '').replace(/_/g, ' ');
            await uploadDocument(file, displayName, 'public', (pct) => {
                setUploadProgress(pct);
            });
            setMessage(`🚀 Ingestion Complete: '${file.name}' is now indexed in the Vector Warehouse.`);
            setTimeout(loadDocs, 1800);
        } catch (err) { setError(`❌ Ingestion Error: ${err.message}`); } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    }

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="admin-page"
            style={{ padding: '2rem 4rem 6rem' }}
        >
            <header className="page-header" style={{ marginBottom: '3rem', display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                <div style={{ background: 'var(--clr-primary)', padding: '0.85rem', borderRadius: '16px', color: '#fff', boxShadow: '0 8px 20px var(--clr-primary-glow)' }}>
                    <Shield size={32} />
                </div>
                <div>
                    <h2 style={{ fontSize: '2rem', fontWeight: 800, margin: 0, letterSpacing: '-0.5px', color: 'var(--clr-text-main)' }}>Management Console</h2>
                    <p style={{ color: 'var(--clr-text-muted)', fontSize: '0.95rem' }}>Governance hub for policies, role-based access, and indexing health.</p>
                </div>
            </header>

            {/* Notifications */}
            <AnimatePresence>
                {message && (
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} style={{ background: 'rgba(0, 255, 127, 0.1)', color: '#00ff7f', padding: '1rem 1.5rem', borderRadius: '16px', marginBottom: '2rem', border: '1px solid rgba(0, 255, 127, 0.2)', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Activity size={18} /> {message}
                    </motion.div>
                )}
                {error && (
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} style={{ background: 'rgba(248, 81, 73, 0.1)', color: '#ff6b6b', padding: '1rem 1.5rem', borderRadius: '16px', marginBottom: '2rem', border: '1px solid rgba(248, 81, 73, 0.2)', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Info size={18} /> {error}
                    </motion.div>
                )}
            </AnimatePresence>

            <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '2.5rem', alignItems: 'start' }}>

                {/* 🗺️ Policy Index */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>

                    <PolicyDiffTool documents={docs} />

                    <motion.div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                            <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                                <FileText size={22} color="var(--clr-primary)" /> Policy Warehouse
                            </h3>
                            <button className="chip" onClick={loadDocs} style={{ cursor: 'pointer', background: 'var(--clr-panel-bg)', border: '1px solid var(--clr-border)', color: 'var(--clr-text-main)', borderRadius: '10px', padding: '6px 14px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <RefreshCw size={14} className={loadingDocs ? 'animate-spin' : ''} /> Refresh
                            </button>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                            {loadingDocs ? <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--clr-text-muted)' }}>Synchronizing context index...</div> :
                                docs.length === 0 ? <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--clr-text-muted)' }}>Index is currently empty.</div> :
                                    docs.map(doc => (
                                        <motion.div
                                            key={doc.id}
                                            whileHover={{ x: 5 }}
                                            style={{
                                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                padding: '1.25rem', background: 'var(--clr-panel-bg)',
                                                border: '1px solid var(--clr-border)', borderRadius: '20px'
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                                                <div style={{ width: 48, height: 48, borderRadius: '14px', background: 'rgba(79, 142, 247, 0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                    <FileText size={24} color="var(--clr-primary)" />
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 700, fontSize: '1rem' }}>{doc.display_name}</div>
                                                    <div style={{ fontSize: '0.8rem', color: 'var(--clr-text-muted)', marginTop: '2px' }}>{doc.filename} • {new Date(doc.uploaded_at).toLocaleDateString()}</div>
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                                                <span className={`badge ${doc.access_level}`}>{doc.access_level}</span>
                                                <button onClick={() => handleDeleteDoc(doc.id)} style={{ background: 'transparent', color: 'var(--clr-error)', border: 'none', cursor: 'pointer', padding: '6px', opacity: 0.6 }}>
                                                    <Trash2 size={20} />
                                                </button>
                                            </div>
                                        </motion.div>
                                    ))
                            }
                        </div>
                    </motion.div>

                    {/* Central Upload */}
                    <motion.div className="card">
                        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                            <UploadCloud size={22} color="var(--clr-primary)" /> Secure Policy Ingestion
                        </h3>
                        <div
                            className={`upload-zone ${isDragOver ? 'dragover' : ''}`}
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={async (e) => { e.preventDefault(); setDragOver(false); const file = e.dataTransfer.files[0]; if (file) performUpload(file); }}
                            onClick={() => !uploading && fileInputRef.current?.click()}
                            style={{
                                padding: '3rem 2rem', border: '2px dashed var(--clr-border)', borderRadius: '24px',
                                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                transition: 'all 0.3s ease', cursor: uploading ? 'not-allowed' : 'pointer',
                                background: isDragOver ? 'rgba(79, 142, 247, 0.05)' : 'transparent',
                                textAlign: 'center'
                            }}
                        >
                            <div style={{ marginBottom: '1.5rem' }}>
                                {uploading ? <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1 }}><Loader2 size={40} color="var(--clr-primary)" /></motion.div> : <UploadCloud size={40} color="var(--clr-text-muted)" />}
                            </div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--clr-text-main)' }}>{uploading ? 'Finalizing Ingestion...' : 'Click or Drag PDF to Index'}</div>
                            <p style={{ fontSize: '0.85rem', color: 'var(--clr-text-muted)', marginTop: '0.5rem' }}>Auto-processing OCR & High-Dimensional Vectors</p>

                            {uploading && (
                                <div style={{ width: '100%', maxWidth: '300px', marginTop: '1.5rem' }}>
                                    <div style={{ width: '100%', background: 'var(--clr-panel-bg)', height: '5px', borderRadius: '3px', overflow: 'hidden' }}>
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${uploadProgress}%` }}
                                            transition={{ type: "spring", stiffness: 50, damping: 15 }}
                                            style={{ height: '100%', background: 'var(--clr-primary)', boxShadow: '0 0 10px var(--clr-primary-glow)' }}
                                        />
                                    </div>
                                    <div style={{ fontSize: '0.75rem', marginTop: '0.8rem', fontWeight: 700, opacity: 0.9 }}>
                                        {uploadProgress < 100 ? `${uploadProgress}% Physical Stream Uploading...` : '⚙️ Server Processing & Indexing...'}
                                    </div>
                                </div>
                            )}
                        </div>
                        <input ref={fileInputRef} type="file" accept=".pdf" style={{ display: 'none' }} onChange={(e) => { const file = e.target.files[0]; if (file) performUpload(file); }} />
                    </motion.div>
                </div>

                {/* 👥 Access & RBAC */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>

                    <motion.div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                            <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.15rem' }}>
                                <Users size={20} color="var(--clr-primary)" /> Sentinel RBAC
                            </h3>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                            {loadingUsers ? <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--clr-text-muted)' }}>Retrieving identity list...</div> :
                                users.map(u => (
                                    <div key={u.id} style={{
                                        padding: '1.25rem', background: 'var(--clr-panel-bg)',
                                        border: '1px solid var(--clr-border)', borderRadius: '20px'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                <div style={{ width: 44, height: 44, borderRadius: '12px', background: 'var(--clr-panel-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                    <UserPlus size={20} color="var(--clr-text-muted)" />
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--clr-text-main)' }}>{u.username}</div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--clr-text-muted)' }}>{u.email}</div>
                                                </div>
                                            </div>
                                            <span className={`badge ${u.role}`}>{u.role}</span>
                                        </div>
                                        <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                            <select
                                                value={u.role}
                                                onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                                style={{
                                                    flex: 1, background: 'var(--clr-input-bg)', color: 'var(--clr-input-text)',
                                                    border: '1px solid var(--clr-border)', borderRadius: '12px',
                                                    fontSize: '0.85rem', padding: '8px 12px', outline: 'none'
                                                }}
                                            >
                                                <option value="public">Public Viewer</option>
                                                <option value="analyst">Analyst (Upload Privileges)</option>
                                                <option value="admin">System Administrator</option>
                                            </select>
                                        </div>
                                    </div>
                                ))
                            }
                        </div>
                    </motion.div>

                    {/* Infrastructure Guard */}
                    <motion.div className="card" style={{ background: 'linear-gradient(135deg, rgba(79, 142, 247, 0.08), transparent)' }}>
                        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.15rem' }}>
                            <Lock size={18} color="var(--clr-primary)" /> Infrastructure Guard
                        </h3>
                        <div style={{ fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: 'var(--clr-text-muted)' }}>RAG Pipeline:</span>
                                <span style={{ fontWeight: 600 }}>RRF Hybrid Fusion</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: 'var(--clr-text-muted)' }}>OCR Resolution:</span>
                                <span>High Density (Verified)</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: 'var(--clr-text-muted)' }}>Service Mesh:</span>
                                <span style={{ color: 'var(--clr-success)', fontWeight: 700 }}>● SECURE</span>
                            </div>
                        </div>
                    </motion.div>

                </div>
            </div>
        </motion.div>
    );
}
