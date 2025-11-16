import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

export default function ChatPanel({
  selectedNode,
  messages,
  onSendMessage,
  loading,
  diagram,
  onWidthChange,
  onClose,
}) {
  const [input, setInput] = useState('');
  const [width, setWidth] = useState(400); // Default width
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const messagesEndRef = useRef(null);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    let rafId = null;
    let pendingWidth = null;

    const handleMouseMove = (e) => {
      if (!isResizing) return;

      // Prevent text selection during resize
      e.preventDefault();

      // Calculate new width based on distance from right edge
      const newWidth = window.innerWidth - e.clientX;

      // Set min/max constraints
      // NOTE: To change minimum panel width, update this value AND the min-width in App.css (.chat-panel)
      if (newWidth >= 150 && newWidth <= 1200) {
        pendingWidth = newWidth;

        // Throttle updates using requestAnimationFrame for smooth 60fps
        if (!rafId) {
          rafId = requestAnimationFrame(() => {
            if (pendingWidth !== null) {
              setWidth(pendingWidth);
              pendingWidth = null;
            }
            rafId = null;
          });
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      // Re-enable text selection
      document.body.style.userSelect = '';

      // Cancel any pending animation frame
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    };

    if (isResizing) {
      // Disable text selection on body during resize
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      // Ensure text selection is re-enabled on cleanup
      document.body.style.userSelect = '';

      // Cancel any pending animation frame on cleanup
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
    };
  }, [isResizing]);

  // Notify parent when width changes (throttled to reduce re-renders)
  useEffect(() => {
    if (onWidthChange) {
      // Throttle parent notifications to every 16ms (60fps) to match RAF updates
      const timerId = setTimeout(() => {
        onWidthChange(width);
      }, 16);

      return () => clearTimeout(timerId);
    }
  }, [width, onWidthChange]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div
      className={`chat-panel ${isMobile ? 'mobile-modal' : ''}`}
      style={isMobile ? {} : { width: `${width}px` }}
    >
      {!isMobile && (
        <div
          className="resize-handle"
          onMouseDown={() => setIsResizing(true)}
        />
      )}
      <div className="chat-header">
        <div>
          <h3>System Chat</h3>
          {selectedNode && (
            <span className="chat-context">
              Context: {selectedNode.data.label} ({selectedNode.data.type})
            </span>
          )}
        </div>
        {isMobile && onClose && (
          <button className="close-button" onClick={onClose} title="Back to diagram">
            ✕
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-role">{msg.role}</div>
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-role">assistant</div>
            <div className="message-content typing">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            selectedNode
              ? `Ask about ${selectedNode.data.label}...`
              : 'Ask about the system...'
          }
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
