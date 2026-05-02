import { motion } from 'framer-motion';

export default function ProgressBar({ progress }) {
    return (
        <div className="upload-progress-container">
            <motion.div
                className="upload-progress-bar"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ type: "spring", stiffness: 50, damping: 15 }}
            />
            <div className="progress-text" style={{ marginTop: '6px', fontSize: '11px', fontWeight: 700, opacity: 0.9 }}>
                {progress < 100 ? `${progress}% Uploaded` : '🚀 Stream Complete — Processing on Server...'}
            </div>
        </div>
    );
}
