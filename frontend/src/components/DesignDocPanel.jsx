import { useState, useEffect, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { toPng } from 'html-to-image';
import { addWatermark } from '../utils/watermark';
import { marked } from 'marked';
import TurndownService from 'turndown';
import { MOBILE_BREAKPOINT } from '../constants/ui';
import { redeemPromoCode } from '../api/client';

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

const LOCKED_SECTIONS = [
  { title: 'System Overview', teaser: 'High-level architecture and the technology choices behind it.' },
  { title: 'Architecture Diagram', teaser: 'Annotated walkthrough of the diagram you just created.' },
  { title: 'Component Details', teaser: 'Each service: responsibility, scaling profile, and failure modes.' },
  { title: 'Data Flow', teaser: 'How a request propagates through your system end-to-end.' },
  { title: 'Scalability & Reliability', teaser: 'Bottlenecks at 10x and 100x current traffic, and how to absorb them.' },
  { title: 'Security Considerations', teaser: 'Auth flow, secrets management, and the threat surface to plan for.' },
  { title: 'Trade-offs & Alternatives', teaser: 'Why this design over the obvious alternatives, with the cost of each.' },
  { title: 'Implementation Phases', teaser: 'Concrete rollout order with dependencies and milestones.' },
];

export default function DesignDocPanel({
  designDoc,
  onSave,
  onClose,
  // sessionId - reserved for future use (e.g., real-time sync)
  onExport,
  isGenerating = false,
  isPreview = false,
  onUpgrade,
  onWidthChange,
  onApplyLayout,
  sessionHistorySidebarWidth = 0,
  syncStatus = null,
  onCreditsUpdated,
}) {
  const [width, setWidth] = useState(400); // Default width
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saving', 'saved', 'error'
  const [saveTimer, setSaveTimer] = useState(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoError, setPromoError] = useState(null);
  const [promoSuccess, setPromoSuccess] = useState(null);

  const handlePromoSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!promoCode.trim()) return;
    setPromoLoading(true);
    setPromoError(null);
    setPromoSuccess(null);
    try {
      const result = await redeemPromoCode(promoCode.trim());
      setPromoSuccess(`+${result.credits_granted} credits added — balance: ${result.new_balance}`);
      setPromoCode('');
      if (onCreditsUpdated) onCreditsUpdated();
    } catch (err) {
      setPromoError(err.response?.data?.detail || err.response?.data?.message || 'Invalid promo code');
    } finally {
      setPromoLoading(false);
    }
  }, [promoCode, onCreditsUpdated]);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
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

  // Lock the editor while showing a free-tier preview so the locked content
  // can't be edited and accidentally persisted as the user's "real" doc.
  useEffect(() => {
    if (editor) {
      editor.setEditable(!isPreview);
    }
  }, [editor, isPreview]);

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

      // Add watermark, then convert to base64 (remove prefix)
      const watermarkedDataUrl = await addWatermark(dataUrl);
      return watermarkedDataUrl.split(',')[1];
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
        } else {
          alert('Could not capture the diagram. This can happen on Safari, try Chrome if the problem persists.');
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
    if (syncStatus?.state === 'running') return '● Syncing with diagram...';
    if (syncStatus?.state === 'pending') return '● Auto-sync queued';
    if (syncStatus?.state === 'failed') return '✗ Sync failed';
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
    if (syncStatus?.state === 'running' || syncStatus?.state === 'pending') {
      return 'save-status saving';
    }
    if (syncStatus?.state === 'failed') return 'save-status error';
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
            <h3>{isPreview ? 'Generating Preview...' : 'Generating Design Document...'}</h3>
            <p>{isPreview
              ? 'Sketch is writing a teaser for your diagram. This usually takes a few seconds.'
              : 'This may take 1-2 minutes. Sketch is analyzing your system architecture and creating a comprehensive design document.'}</p>
          </div>
        ) : (
          <>
            <EditorContent editor={editor} />
            {isPreview && (
              <div className="design-doc-locked">
                <div className="design-doc-locked-banner">
                  <div className="design-doc-locked-banner-text">
                    <strong>The rest of your design doc is locked.</strong>
                    <span>Upgrade to Starter ($1/mo) to unlock all 8 sections below for your diagram.</span>
                  </div>
                  <button className="design-doc-locked-button" onClick={onUpgrade}>
                    Upgrade to unlock
                  </button>
                </div>
                <form className="design-doc-locked-promo" onSubmit={handlePromoSubmit}>
                  <span className="design-doc-locked-promo-label">Or redeem code <code>FREE100</code> for 100 credits:</span>
                  <input
                    type="text"
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                    placeholder="Enter code"
                    className="design-doc-locked-promo-input"
                    disabled={promoLoading}
                    aria-label="Promo code"
                  />
                  <button
                    type="submit"
                    className="design-doc-locked-promo-submit"
                    disabled={promoLoading || !promoCode.trim()}
                  >
                    {promoLoading ? '...' : 'Apply'}
                  </button>
                  {promoError && <span className="design-doc-locked-promo-error">{promoError}</span>}
                  {promoSuccess && <span className="design-doc-locked-promo-success">{promoSuccess}</span>}
                </form>
                <div className="design-doc-locked-blur">
                  {LOCKED_SECTIONS.map(({ title, teaser }) => (
                    <div className="design-doc-locked-section" key={title}>
                      <h2>{title}</h2>
                      <p className="design-doc-locked-teaser">{teaser}</p>
                      <div className="design-doc-locked-line" style={{ width: '92%' }} />
                      <div className="design-doc-locked-line" style={{ width: '78%' }} />
                      <div className="design-doc-locked-line" style={{ width: '85%' }} />
                      <div className="design-doc-locked-line" style={{ width: '64%' }} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="design-doc-footer">
        <div className={getSaveStatusClass()}>
          {isPreview ? 'Preview' : getSaveStatusText()}
        </div>
        <div className="export-buttons">
          <select
            onChange={(e) => {
              if (e.target.value) {
                handleExport(e.target.value);
                e.target.value = ''; // Reset dropdown
              }
            }}
            disabled={exportLoading || isPreview}
            className="export-dropdown"
            title={isPreview ? 'Upgrade to export your design document' : undefined}
          >
            <option value="">{exportLoading ? 'Exporting...' : 'Export'}</option>
            <option value="pdf">PDF</option>
            <option value="markdown">Markdown</option>
            <option value="png">PNG</option>
          </select>
        </div>
      </div>
    </div>
  );
}
