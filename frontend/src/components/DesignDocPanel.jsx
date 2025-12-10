import { useState, useEffect, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { toPng } from 'html-to-image';
import { marked } from 'marked';
import TurndownService from 'turndown';

// Initialize markdown-to-HTML converter
marked.setOptions({
  breaks: true,
  gfm: true,
});

// Initialize HTML-to-markdown converter
const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
});

export default function DesignDocPanel({
  designDoc,
  onSave,
  onClose,
  // sessionId - reserved for future use (e.g., real-time sync)
  onExport,
  isGenerating = false,
  onWidthChange,
  onApplyLayout,
  sessionHistorySidebarWidth = 0,
}) {
  const [width, setWidth] = useState(400); // Default width
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saving', 'saved', 'error'
  const [saveTimer, setSaveTimer] = useState(null);
  const [exportLoading, setExportLoading] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Initialize Tiptap editor
  const editor = useEditor({
    extensions: [StarterKit],
    content: designDoc ? marked.parse(designDoc) : '',
    onUpdate: ({ editor }) => {
      // Debounced auto-save
      if (saveTimer) {
        clearTimeout(saveTimer);
      }

      setSaveStatus('editing');

      const timer = setTimeout(() => {
        handleSave(editor.getHTML());
      }, 3000); // 3 second debounce

      setSaveTimer(timer);
    },
  });

  // Update editor content when designDoc prop changes (from chat updates)
  useEffect(() => {
    if (editor) {
      if (designDoc) {
        // Convert markdown to HTML for Tiptap
        const htmlContent = marked.parse(designDoc);

        // Only update if content is different (avoid infinite loops)
        if (editor.getHTML() !== htmlContent) {
          editor.commands.setContent(htmlContent);
        }
      } else {
        // Clear editor content when designDoc is null (switching to session without doc)
        editor.commands.setContent('');
      }
    }
  }, [designDoc, editor]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (saveTimer) {
        clearTimeout(saveTimer);
      }
    };
  }, [saveTimer]);

  // Notify parent when width changes (throttled to reduce re-renders)
  useEffect(() => {
    if (onWidthChange) {
      // Throttle parent notifications to every 16ms (60fps) to match RAF updates
      // This syncs with the panel's 60fps resize for smooth movement
      const timerId = setTimeout(() => {
        onWidthChange(width);
      }, 16);

      return () => clearTimeout(timerId);
    }
  }, [width, onWidthChange]);

  // Handle resize
  useEffect(() => {
    let rafId = null;
    let pendingWidth = null;

    const handleMouseMove = (e) => {
      if (!isResizing) return;

      // Prevent text selection during resize
      e.preventDefault();

      // Calculate new width based on mouse X position
      // Account for session history sidebar offset
      const newWidth = e.clientX - sessionHistorySidebarWidth;

      // Set min/max constraints
      // NOTE: To change minimum panel width, update this value AND the min-width in App.css (.design-doc-panel)
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
  }, [isResizing, sessionHistorySidebarWidth]);

  const handleSave = async (htmlContent) => {
    setSaveStatus('saving');
    try {
      // Convert HTML back to markdown for backend storage
      const markdownContent = turndownService.turndown(htmlContent);
      await onSave(markdownContent);
      setSaveStatus('saved');
    } catch (error) {
      console.error('Failed to save design doc:', error);
      setSaveStatus('error');
    }
  };

  const captureDiagramScreenshot = useCallback(async () => {
    const diagramElement = document.querySelector('.react-flow__viewport');
    if (!diagramElement) {
      console.error('Diagram element not found');
      return null;
    }

    try {
      // Apply layout before capturing to ensure clean organization
      if (onApplyLayout) {
        console.log('Applying layout before screenshot...');
        onApplyLayout();
        // Wait for layout animation to complete (400ms animation + 100ms buffer)
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // Hide edge labels using opacity to avoid rendering artifacts
      // Using opacity: 0 instead of display: none or removing from DOM
      const edgeTexts = document.querySelectorAll('.react-flow__edge-text');
      const edgeTextBgs = document.querySelectorAll('.react-flow__edge-textbg');

      // Store original opacity values
      const originalStyles = [];

      edgeTexts.forEach((el) => {
        originalStyles.push({ element: el, opacity: el.style.opacity });
        el.style.opacity = '0';
      });

      edgeTextBgs.forEach((el) => {
        originalStyles.push({ element: el, opacity: el.style.opacity });
        el.style.opacity = '0';
      });

      // Small delay to ensure styles are applied
      await new Promise(resolve => setTimeout(resolve, 50));

      const dataUrl = await toPng(diagramElement, {
        quality: 1.0,
        pixelRatio: 2,
      });

      // Restore all original styles
      originalStyles.forEach(({ element, opacity }) => {
        element.style.opacity = opacity;
      });

      // Convert data URL to base64 (remove "data:image/png;base64," prefix)
      return dataUrl.split(',')[1];
    } catch (error) {
      console.error('Failed to capture diagram:', error);
      return null;
    }
  }, [onApplyLayout]);

  const handleExport = async (format) => {
    setExportLoading(true);
    try {
      const diagramImage = await captureDiagramScreenshot();

      // PNG export: Just download the diagram screenshot (no backend call)
      if (format === 'png') {
        if (diagramImage) {
          // Convert base64 to blob and download
          const byteCharacters = atob(diagramImage);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], { type: 'image/png' });

          // Download
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = 'diagram.png';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        }
      } else {
        // PDF or Markdown: Call backend
        await onExport(format, diagramImage);
      }
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export design document. Please try again.');
    } finally {
      setExportLoading(false);
    }
  };

  const getSaveStatusText = () => {
    switch (saveStatus) {
      case 'saving':
        return '● Saving...';
      case 'saved':
        return '✓ Saved';
      case 'error':
        return '✗ Failed to save';
      case 'editing':
        return '● Editing...';
      default:
        return '';
    }
  };

  const getSaveStatusClass = () => {
    switch (saveStatus) {
      case 'saving':
      case 'editing':
        return 'save-status saving';
      case 'saved':
        return 'save-status saved';
      case 'error':
        return 'save-status error';
      default:
        return 'save-status';
    }
  };

  const handleResizeStart = () => {
    setIsResizing(true);
  };

  return (
    <div
      className={`design-doc-panel ${isMobile ? 'mobile-modal' : ''}`}
      style={isMobile ? {} : { width: `${width}px`, left: `${sessionHistorySidebarWidth}px` }}
    >
      {!isMobile && (
        <div
          className="resize-handle-right"
          onMouseDown={handleResizeStart}
        />
      )}
      <div className="design-doc-header">
        <div>
          <h3>Design Document</h3>
        </div>
        <button className="close-button" onClick={onClose} title="Close">
          ✕
        </button>
      </div>

      <div className="design-doc-toolbar">
        {editor && (
          <>
            <button
              onClick={() => editor.chain().focus().toggleBold().run()}
              className={editor.isActive('bold') ? 'is-active' : ''}
              title="Bold"
            >
              <strong>B</strong>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className={editor.isActive('italic') ? 'is-active' : ''}
              title="Italic"
            >
              <em>I</em>
            </button>
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
              className={editor.isActive('heading', { level: 1 }) ? 'is-active' : ''}
              title="Heading 1"
            >
              H1
            </button>
            <button
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={editor.isActive('heading', { level: 2 }) ? 'is-active' : ''}
              title="Heading 2"
            >
              H2
            </button>
            <button
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={editor.isActive('bulletList') ? 'is-active' : ''}
              title="Bullet List"
            >
              •••
            </button>
            <button
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={editor.isActive('orderedList') ? 'is-active' : ''}
              title="Numbered List"
            >
              123
            </button>
          </>
        )}
      </div>

      <div className="design-doc-editor">
        {isGenerating ? (
          <div className="generating-overlay">
            <div className="generating-spinner"></div>
            <h3>Generating Design Document...</h3>
            <p>This may take 1-2 minutes. Sketch is analyzing your system architecture and creating a comprehensive design document.</p>
          </div>
        ) : (
          <EditorContent editor={editor} />
        )}
      </div>

      <div className="design-doc-footer">
        <div className={getSaveStatusClass()}>
          {getSaveStatusText()}
        </div>
        <div className="export-buttons">
          <select
            onChange={(e) => {
              if (e.target.value) {
                handleExport(e.target.value);
                e.target.value = ''; // Reset dropdown
              }
            }}
            disabled={exportLoading}
            className="export-dropdown"
          >
            <option value="">Export ▼</option>
            <option value="pdf">📕 PDF</option>
            <option value="markdown">📝 Markdown</option>
            <option value="png">🖼️ PNG</option>
          </select>
        </div>
      </div>
    </div>
  );
}
