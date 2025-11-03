import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const CodeViewer = ({ skeleton }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!skeleton) {
    return null;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(skeleton.code);
    // Could add a toast notification here
  };

  return (
    <div className="code-viewer">
      <div className="code-viewer-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="code-viewer-title">
          <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
          <span className="code-language">{skeleton.language.toUpperCase()}</span>
          <span className="code-info">
            {skeleton.classes?.length > 0 && ` • ${skeleton.classes.length} class${skeleton.classes.length !== 1 ? 'es' : ''}`}
            {skeleton.functions?.length > 0 && ` • ${skeleton.functions.length} function${skeleton.functions.length !== 1 ? 's' : ''}`}
          </span>
        </div>
        <button
          className="copy-button"
          onClick={(e) => {
            e.stopPropagation();
            handleCopy();
          }}
          title="Copy code"
        >
          📋 Copy
        </button>
      </div>

      {isExpanded && (
        <div className="code-viewer-content">
          <SyntaxHighlighter
            language={skeleton.language}
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              borderRadius: '0 0 8px 8px',
              fontSize: '13px',
              maxHeight: '400px',
            }}
            showLineNumbers
          >
            {skeleton.code}
          </SyntaxHighlighter>
        </div>
      )}

      <style jsx>{`
        .code-viewer {
          background: #1e1e1e;
          border-radius: 8px;
          margin-bottom: 16px;
          overflow: hidden;
          border: 1px solid #3e3e3e;
        }

        .code-viewer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: #2d2d2d;
          cursor: pointer;
          user-select: none;
        }

        .code-viewer-header:hover {
          background: #333;
        }

        .code-viewer-title {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #d4d4d4;
          font-size: 14px;
          font-weight: 500;
        }

        .toggle-icon {
          color: #888;
          font-size: 12px;
          width: 16px;
        }

        .code-language {
          color: #4ec9b0;
          font-weight: 600;
          text-transform: uppercase;
        }

        .code-info {
          color: #888;
          font-size: 12px;
        }

        .copy-button {
          background: #0e639c;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 12px;
          cursor: pointer;
          transition: background 0.2s;
        }

        .copy-button:hover {
          background: #1177bb;
        }

        .copy-button:active {
          background: #0d5a8f;
        }

        .code-viewer-content {
          overflow: auto;
        }
      `}</style>
    </div>
  );
};

export default CodeViewer;
