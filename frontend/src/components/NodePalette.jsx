import { useState, useEffect } from 'react';
import './NodePalette.css';

const NODE_TYPES = [
  {
    value: 'database',
    label: 'Database',
    description: 'Persistent data storage (SQL, NoSQL, etc.)'
  },
  {
    value: 'cache',
    label: 'Cache',
    description: 'In-memory data store for fast retrieval'
  },
  {
    value: 'server',
    label: 'Server',
    description: 'Application or web server'
  },
  {
    value: 'api',
    label: 'API',
    description: 'REST, GraphQL, or other API endpoint'
  },
  {
    value: 'loadbalancer',
    label: 'Load Balancer',
    description: 'Distributes traffic across multiple servers'
  },
  {
    value: 'queue',
    label: 'Queue',
    description: 'Message queue for async processing'
  },
  {
    value: 'cdn',
    label: 'CDN',
    description: 'Content delivery network for static assets'
  },
  {
    value: 'gateway',
    label: 'Gateway',
    description: 'API gateway or entry point'
  },
  {
    value: 'storage',
    label: 'Storage',
    description: 'Object or file storage (S3, etc.)'
  },
  {
    value: 'service',
    label: 'Service',
    description: 'Microservice or background service'
  },
];

export default function NodePalette({ isOpen, onClose, onSelectType, designDocOpen, designDocWidth, chatPanelOpen, chatPanelWidth, sessionHistoryOpen, sessionHistorySidebarWidth }) {
  const [hoveredType, setHoveredType] = useState(null);
  const [height, setHeight] = useState(120); // Default height
  const [isResizing, setIsResizing] = useState(false);

  // Handle resize with RAF throttling
  useEffect(() => {
    let rafId = null;
    let pendingHeight = null;

    const handleMouseMove = (e) => {
      if (!isResizing) return;

      // Calculate new height based on distance from bottom of screen
      const newHeight = window.innerHeight - e.clientY;

      // Set min/max constraints
      if (newHeight >= 60 && newHeight <= 800) {
        pendingHeight = newHeight;

        // Throttle updates using requestAnimationFrame for smooth 60fps
        if (!rafId) {
          rafId = requestAnimationFrame(() => {
            if (pendingHeight !== null) {
              setHeight(pendingHeight);
              pendingHeight = null;
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

  if (!isOpen) return null;

  // Calculate palette positioning based on panel states
  // Session history sidebar (left) + design doc panel (left)
  const leftOffset = (sessionHistoryOpen ? sessionHistorySidebarWidth : 0) + (designDocOpen ? designDocWidth : 0);
  const rightOffset = chatPanelOpen ? chatPanelWidth : 0;

  return (
    <div
      className={`node-palette ${isOpen ? 'open' : ''}`}
      style={{
        left: `${leftOffset}px`,
        right: chatPanelOpen ? `${rightOffset}px` : '0px',
        height: `${height}px`
      }}
    >
        {/* Resize handle at top */}
        <div
          className="resize-handle-top"
          onMouseDown={() => setIsResizing(true)}
        />

        <div className="palette-header">
          <h3>Add Component</h3>
          <button className="palette-close-btn" onClick={onClose} title="Close">
            ✕
          </button>
        </div>

        <div className="palette-content">
          <div className="node-type-grid">
            {NODE_TYPES.map((nodeType) => (
              <div
                key={nodeType.value}
                className={`node-type-card node-type-${nodeType.value}`}
                onClick={() => onSelectType(nodeType.value)}
                onMouseEnter={() => setHoveredType(nodeType.value)}
                onMouseLeave={() => setHoveredType(null)}
              >
                <div className={`node-type-color-bar node-type-${nodeType.value}`} />
                <div className="node-type-label">{nodeType.label}</div>

                {/* Tooltip */}
                {hoveredType === nodeType.value && (
                  <div className="node-type-tooltip">
                    {nodeType.description}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
    </div>
  );
}
