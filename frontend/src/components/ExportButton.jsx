import { useState } from 'react';
import { toPng } from 'html-to-image';
import { exportDesignDoc } from '../api/client';

export default function ExportButton({ sessionId }) {
  const [loading, setLoading] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const captureDiagram = async () => {
    // Find the React Flow viewport element
    const viewport = document.querySelector('.react-flow__viewport');
    if (!viewport) {
      console.error('Could not find diagram viewport');
      return null;
    }

    // Find all edge labels and temporarily hide them
    const edgeLabels = document.querySelectorAll('.react-flow__edge-text, .react-flow__edge-textbg');
    const originalDisplayValues = [];

    edgeLabels.forEach((label) => {
      originalDisplayValues.push(label.style.display);
      label.style.display = 'none';
    });

    try {
      // Small delay to ensure labels are hidden before capture
      await new Promise(resolve => setTimeout(resolve, 100));

      // Capture the diagram as PNG with better quality settings
      const dataUrl = await toPng(viewport, {
        backgroundColor: '#ffffff',
        quality: 0.95,
        pixelRatio: 2, // Higher resolution for better quality
        cacheBust: true, // Avoid caching issues
        style: {
          transform: 'none', // Reset any transforms
        }
      });

      // Convert data URL to base64 string (remove the "data:image/png;base64," prefix)
      const base64 = dataUrl.split(',')[1];
      return base64;
    } catch (error) {
      console.error('Failed to capture diagram:', error);
      return null;
    } finally {
      // Restore edge labels
      edgeLabels.forEach((label, index) => {
        label.style.display = originalDisplayValues[index];
      });
    }
  };

  const handleExport = async (format) => {
    if (!sessionId) {
      alert('No active session to export');
      return;
    }

    setLoading(true);
    setShowMenu(false);

    try {
      console.log(`Exporting design doc in format: ${format}`);

      // Capture the diagram screenshot
      const diagramImage = await captureDiagram();
      if (!diagramImage) {
        alert('Failed to capture diagram. Please try again.');
        setLoading(false);
        return;
      }

      // If PNG only, just download the image directly
      if (format === 'png') {
        const pngBlob = base64ToBlob(diagramImage, 'image/png');
        downloadFile(pngBlob, 'diagram.png');
        console.log('Diagram PNG downloaded successfully');
        setLoading(false);
        return;
      }

      const response = await exportDesignDoc(sessionId, format, diagramImage);

      // Download PDF if available
      if (response.pdf) {
        const pdfBlob = base64ToBlob(response.pdf.content, 'application/pdf');
        downloadFile(pdfBlob, response.pdf.filename);
      }

      // Download markdown if available
      if (response.markdown) {
        const markdownBlob = new Blob([response.markdown.content], { type: 'text/markdown' });
        downloadFile(markdownBlob, response.markdown.filename);
      }

      // Download diagram PNG if available (for markdown format)
      if (response.diagram_png) {
        const pngBlob = base64ToBlob(response.diagram_png.content, 'image/png');
        downloadFile(pngBlob, response.diagram_png.filename);
      }

      console.log('Design document exported successfully');
    } catch (error) {
      console.error('Failed to export design doc:', error);
      alert('Failed to generate design document. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const base64ToBlob = (base64, mimeType) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  const downloadFile = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  return (
    <div className="export-button-container">
      <button
        className="export-button"
        onClick={() => setShowMenu(!showMenu)}
        disabled={loading}
      >
        {loading ? 'Generating...' : '📄 Export Design Doc'}
      </button>

      {showMenu && !loading && (
        <div className="export-menu">
          <button onClick={() => handleExport('png')}>
            🖼️ Export as PNG
          </button>
          <button onClick={() => handleExport('pdf')}>
            📕 Export as PDF
          </button>
          <button onClick={() => handleExport('markdown')}>
            📝 Export as Markdown
          </button>
          <button onClick={() => handleExport('both')}>
            📦 Export PDF + Markdown
          </button>
        </div>
      )}
    </div>
  );
}
