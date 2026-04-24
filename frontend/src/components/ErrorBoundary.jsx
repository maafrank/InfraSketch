import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    if (typeof console !== 'undefined') {
      console.error('[ErrorBoundary] Uncaught render error:', error, errorInfo);
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    const { error, errorInfo } = this.state;
    const userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown';

    return (
      <div
        style={{
          minHeight: '100vh',
          padding: '24px',
          background: '#0a0a0a',
          color: '#e5e5e5',
          fontFamily: 'JetBrains Mono, ui-monospace, Menlo, monospace',
          fontSize: '13px',
          lineHeight: 1.5,
          overflowY: 'auto',
        }}
      >
        <div style={{ maxWidth: '860px', margin: '0 auto' }}>
          <h1 style={{ color: '#ff6b6b', fontSize: '18px', marginBottom: '12px' }}>
            InfraSketch hit a runtime error
          </h1>
          <p style={{ marginBottom: '16px', color: '#aaa' }}>
            Something went wrong while rendering. Details below, please share them if the problem persists.
          </p>
          <button
            onClick={this.handleReload}
            style={{
              padding: '8px 16px',
              background: '#2a2a2a',
              color: '#e5e5e5',
              border: '1px solid #444',
              borderRadius: '4px',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '13px',
              marginBottom: '24px',
            }}
          >
            Reload
          </button>
          <div
            style={{
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: '4px',
              padding: '16px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            <div style={{ color: '#ff6b6b', marginBottom: '8px', fontWeight: 600 }}>
              {error.name}: {error.message}
            </div>
            {error.stack && (
              <div style={{ color: '#aaa', fontSize: '12px' }}>{error.stack}</div>
            )}
            {errorInfo && errorInfo.componentStack && (
              <div style={{ color: '#777', fontSize: '12px', marginTop: '12px' }}>
                Component stack:{errorInfo.componentStack}
              </div>
            )}
            <div style={{ color: '#555', fontSize: '11px', marginTop: '16px' }}>
              {userAgent}
            </div>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
