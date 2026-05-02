import React from 'react';

export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
        this.setState({ errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '2rem', color: '#ff6b6b', background: '#1a1025', height: '100vh', width: '100vw', fontFamily: 'monospace' }}>
                    <h2>React Crash Detected 🚀🔥</h2>
                    <p>{this.state.error?.toString()}</p>
                    <pre style={{ color: '#aaa', fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
                        {this.state.errorInfo?.componentStack}
                    </pre>
                </div>
            );
        }
        return this.props.children;
    }
}
