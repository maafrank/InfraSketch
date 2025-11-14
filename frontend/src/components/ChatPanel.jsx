import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

export default function ChatPanel({
  selectedNode,
  messages,
  onSendMessage,
  loading,
  diagram,
  onWidthChange,
}) {
  const [input, setInput] = useState('');
  const [width, setWidth] = useState(400); // Default width
  const [isResizing, setIsResizing] = useState(false);
  const messagesEndRef = useRef(null);

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

      // Calculate new width based on distance from right edge
      const newWidth = window.innerWidth - e.clientX;

      // Set min/max constraints
      if (newWidth >= 300 && newWidth <= 1200) {
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

      // Cancel any pending animation frame
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);

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
    <div className="chat-panel" style={{ width: `${width}px` }}>
      <div
        className="resize-handle"
        onMouseDown={() => setIsResizing(true)}
      />
      <div className="chat-header">
        <div>
          <h3>System Chat</h3>
          {selectedNode && (
            <span className="chat-context">
              Context: {selectedNode.data.label} ({selectedNode.data.type})
            </span>
          )}
        </div>
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
