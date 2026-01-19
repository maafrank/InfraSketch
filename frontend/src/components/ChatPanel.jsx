import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

export default function ChatPanel({
  selectedNode,
  messages,
  onSendMessage,
  loading,
  loadingStepText,
  // diagram - reserved for future use (e.g., context display)
  onWidthChange,
  onClose,
  onExitNodeFocus,
  examplePrompt,
  currentModel,
  onModelChange,
  prefillText,
  suggestions = [],
  onSuggestionClick,
}) {
  const [input, setInput] = useState('');
  const [width, setWidth] = useState(400); // Default width
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

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

  // Auto-resize textarea based on content (up to 10 lines)
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';

      // Calculate line height (approximately 24px with padding)
      const lineHeight = 24;
      const maxLines = 10;
      const maxHeight = lineHeight * maxLines;

      // Set height based on content, capped at max height
      const newHeight = Math.min(textarea.scrollHeight, maxHeight);
      textarea.style.height = `${newHeight}px`;
    }
  }, [input]);

  // Populate input when example prompt is provided
  useEffect(() => {
    if (examplePrompt) {
      setInput(examplePrompt);
      // Auto-focus the textarea
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [examplePrompt]);

  // Track the last prefill we applied so we know when to clear
  const lastAppliedPrefillRef = useRef(null);

  // Populate input when prefillText is provided (for tutorial)
  // Also clear input when prefillText is cleared (tutorial step advancement)
  useEffect(() => {
    if (prefillText) {
      setInput(prefillText);
      lastAppliedPrefillRef.current = prefillText;
      // Auto-focus the textarea
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    } else if (lastAppliedPrefillRef.current) {
      // Clear input when prefillText is cleared AND we had previously applied a prefill
      // This ensures we only clear when transitioning from prefilled -> empty
      // and not when the component first mounts with no prefill
      setInput('');
      lastAppliedPrefillRef.current = null;
    }
  }, [prefillText]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
    // Shift+Enter allows new line (default textarea behavior)
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
        <div className="chat-header-content">
          <div className="chat-header-row">
            <select
              id="chat-model-select"
              value={currentModel}
              onChange={(e) => onModelChange(e.target.value)}
              disabled={loading}
              className="model-select"
            >
              <option value="claude-haiku-4-5">Claude Haiku 4.5</option>
              <option value="claude-sonnet-4-5">Claude Sonnet 4.5</option>
              <option value="claude-opus-4-5">Claude Opus 4.5</option>
            </select>
            {selectedNode && (
              <span className="chat-context">
                {selectedNode.data.label} ({selectedNode.data.type})
              </span>
            )}
            {isMobile && onClose && (
              <button className="close-button" onClick={onClose} title="Back to diagram">
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-role">{msg.role === 'assistant' ? 'Sketch' : msg.role}</div>
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-role">Sketch</div>
            <div className="message-content typing">Thinking...</div>
          </div>
        )}
        {loadingStepText && (
          <div className="message assistant">
            <div className="message-role">Sketch</div>
            <div className="message-content typing">{loadingStepText}</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {selectedNode && !isMobile && onExitNodeFocus && (
        <div className="node-focus-indicator">
          <span>Chatting about: <strong>{selectedNode.data.label}</strong></span>
          <button
            className="exit-node-focus-button"
            onClick={onExitNodeFocus}
            title="Return to system chat"
            type="button"
          >
            ✕
          </button>
        </div>
      )}

      {/* AI-generated suggestion pills */}
      {suggestions.length > 0 && !loading && (
        <div className="chat-suggestions">
          {suggestions.map((suggestion, idx) => (
            <button
              key={idx}
              className="chat-suggestion-pill"
              onClick={() => onSuggestionClick?.(suggestion)}
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            selectedNode
              ? `Ask about ${selectedNode.data.label}...`
              : 'Ask about the system...'
          }
          rows={1}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
