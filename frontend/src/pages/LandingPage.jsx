import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Search, Zap, Files } from 'lucide-react';
import '../index.css';

export default function LandingPage({ onStart }) {
    // Animation variants
    const containerVars = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.15 }
        }
    };

    const itemVars = {
        hidden: { opacity: 0, y: 30 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 70 } }
    };

    return (
        <div className="landing-container" style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '4rem 1rem',
            background: 'var(--clr-bg-main)',
            color: 'var(--clr-text-main)',
            position: 'relative',
            overflowX: 'hidden'
        }}>

            {/* Background Glows mapped to our deep purple/neon theme */}
            <div style={{
                position: 'absolute', top: '-10%', left: '50%', transform: 'translateX(-50%)',
                width: '80vw', height: '50vh', background: 'radial-gradient(ellipse at top, rgba(138,43,226,0.2) 0%, transparent 60%)',
                pointerEvents: 'none', zIndex: 0
            }} />

            <motion.div
                variants={containerVars} initial="hidden" animate="show"
                style={{ zIndex: 1, maxWidth: '1000px', width: '100%', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2rem' }}
            >
                {/* Header Badge */}
                <motion.div variants={itemVars} style={{
                    padding: '0.4rem 1rem', borderRadius: '30px', background: 'rgba(138,43,226,0.1)',
                    border: '1px solid var(--clr-border)', display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                    fontSize: '0.85rem', fontWeight: 600, color: 'var(--clr-primary)', marginBottom: '1rem'
                }}>
                    <Zap size={14} /> Next-Generation Analysis
                </motion.div>

                {/* Huge Hero Text */}
                <motion.h1 variants={itemVars} style={{
                    fontSize: 'clamp(2.5rem, 6vw, 4.5rem)', fontWeight: 800, lineHeight: 1.1, letterSpacing: '-0.03em', margin: 0
                }}>
                    Boost your <br />
                    <span style={{
                        background: 'linear-gradient(to right, #8a2be2, #00f0ff)',
                        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                        textShadow: '0 0 30px rgba(138,43,226,0.3)'
                    }}>research with AI.</span>
                </motion.h1>

                <motion.p variants={itemVars} style={{
                    fontSize: '1.1rem', color: 'var(--clr-text-muted)', maxWidth: '600px', lineHeight: 1.6
                }}>
                    Elevate your policy analysis with context-aware AI. Instantly query vast document repositories, cross-reference clauses, and extract insights with high-precision grounded citations.
                </motion.p>

                {/* CTA Button */}
                <motion.button
                    variants={itemVars}
                    whileHover={{ scale: 1.05, boxShadow: '0 0 30px var(--clr-primary-glow)' }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onStart}
                    style={{
                        marginTop: '1.5rem', padding: '1rem 2.5rem', borderRadius: '12px',
                        background: 'var(--clr-text-main)', color: 'var(--clr-bg-main)',
                        border: 'none', fontSize: '1.1rem', fontWeight: 700, cursor: 'pointer',
                        transition: 'all 0.3s ease'
                    }}
                >
                    Start Analyzing
                </motion.button>

                {/* Value Prop Cards Grid */}
                <motion.div variants={containerVars} style={{
                    display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '1.5rem', width: '100%', marginTop: '5rem', textAlign: 'left'
                }}>
                    <FeatureCard
                        icon={<Search size={24} color="#00f0ff" />}
                        title="Semantic Retrieval"
                        desc="Hybrid search combining BM25 keywords and Vector embeddings to find exactly what you need."
                    />
                    <FeatureCard
                        icon={<Files size={24} color="#8a2be2" />}
                        title="Cross-Document Diffing"
                        desc="Compare variations across multiple policy instances seamlessly with highlighted contexts."
                    />
                    <FeatureCard
                        icon={<Shield size={24} color="#00e676" />}
                        title="Local Data Sovereignty"
                        desc="Run queries entirely offline using Llama 3 to guarantee absolute privacy for sensitive docs."
                    />
                </motion.div>
            </motion.div>
        </div>
    );
}

function FeatureCard({ icon, title, desc }) {
    return (
        <motion.div
            whileHover={{ y: -5, borderColor: 'rgba(138,43,226,0.4)' }}
            style={{
                padding: '2rem', borderRadius: '16px', background: 'var(--clr-bg-card)',
                border: '1px solid var(--clr-border)', display: 'flex', flexDirection: 'column', gap: '1rem',
                backdropFilter: 'blur(10px)', transition: 'all 0.3s ease'
            }}
        >
            <div style={{
                width: 50, height: 50, borderRadius: '12px', background: 'rgba(0,0,0,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(255,255,255,0.05)'
            }}>
                {icon}
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--clr-text-main)', margin: 0 }}>{title}</h3>
            <p style={{ color: 'var(--clr-text-muted)', lineHeight: 1.5, fontSize: '0.95rem', margin: 0 }}>{desc}</p>
        </motion.div>
    );
}
