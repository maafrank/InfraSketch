import { useState, useEffect, useMemo, useCallback } from 'react';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth, useClerk } from "@clerk/clerk-react";
import { toPng } from 'html-to-image';
import LandingPage from './components/LandingPage';
import LoadingAnimation from './components/LoadingAnimation';
import DiagramCanvas from './components/DiagramCanvas';
import ChatPanel from './components/ChatPanel';
import DesignDocPanel from './components/DesignDocPanel';
import AddNodeModal from './components/AddNodeModal';
import {
  generateDiagram,
  sendChatMessage,
  addNode,
  deleteNode,
  updateNode,
  addEdge,
  deleteEdge,
  generateDesignDoc,
  pollDesignDocStatus,
  updateDesignDoc,
  exportDesignDoc,
  setClerkTokenGetter
} from './api/client';
import './App.css';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [diagram, setDiagram] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [showAddNodeModal, setShowAddNodeModal] = useState(false);
  const [preSelectedNodeType, setPreSelectedNodeType] = useState(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [applyLayoutFn, setApplyLayoutFn] = useState(null);

  // Design doc state
  const [designDoc, setDesignDoc] = useState(null);
  const [designDocOpen, setDesignDocOpen] = useState(false);
  const [designDocLoading, setDesignDocLoading] = useState(false);
  const [designDocWidth, setDesignDocWidth] = useState(400);

  // Chat panel state
  const [chatPanelWidth, setChatPanelWidth] = useState(400);

  // Mobile detection
  const [isMobile, setIsMobile] = useState(false);

  // Auth - Set up token getter for API client
  const { getToken, isSignedIn } = useAuth();
  const { openSignIn } = useClerk();

  useEffect(() => {
    // Provide getToken function to API client for auth headers
    setClerkTokenGetter(getToken);
  }, [getToken]);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleGenerate = async (prompt, model) => {
    // Check if user is signed in, redirect to sign-in if not
    if (!isSignedIn) {
      openSignIn();
      return;
    }

    setLoading(true);
    try {
      const response = await generateDiagram(prompt, model);
      console.log('API Response:', response);
      console.log('Diagram:', response.diagram);
      console.log('Nodes:', response.diagram?.nodes);
      console.log('Edges:', response.diagram?.edges);
      setSessionId(response.session_id);
      setDiagram(response.diagram);
      setSelectedNode(null);

      // Generate system summary
      const nodeCount = response.diagram?.nodes?.length || 0;
      const nodeTypes = [...new Set(response.diagram?.nodes?.map(n => n.type) || [])];
      const summary = `## System Overview

I've generated a system architecture with **${nodeCount} components**.

### Component Types
${nodeTypes.map(type => `- **${type}**`).join('\n')}

### What's Next?
- **Click any node** to focus the conversation on that component
- **Ask questions** about the overall system design
- **Request changes** to add, remove, or modify components

Feel free to explore the diagram and ask me anything!`;

      setMessages([
        { role: 'user', content: prompt },
        { role: 'assistant', content: summary }
      ]);
    } catch (error) {
      console.error('Failed to generate diagram:', error);

      // Provide specific error messages based on error type
      let errorMessage = 'Failed to generate diagram. Please try again.';

      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        errorMessage = 'Request timed out. Sonnet 4.5 can take 30+ seconds for complex diagrams. Try:\n\n1. Simplify your prompt\n2. Use Haiku 4.5 (faster, same quality for most cases)\n3. Try again in a moment';
      } else if (error.response?.status === 504) {
        errorMessage = 'Gateway timeout. The request took too long. Try:\n\n1. Use Haiku 4.5 instead (much faster)\n2. Simplify your architecture prompt\n3. Try again in a moment';
      } else if (!error.response) {
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (error.response?.status >= 500) {
        errorMessage = `Server error (${error.response.status}). Please try again in a moment.`;
      }

      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = useCallback((node) => {
    // Only add context message if selecting a different node
    if (selectedNode?.id !== node.id) {
      const contextMessage = {
        role: 'system',
        content: `*Now focusing on: **${node.data.label}** (${node.data.type})*`,
      };
      setMessages((prev) => [...prev, contextMessage]);
    }
    setSelectedNode(node);
  }, [selectedNode]);

  const handleSendMessage = async (message) => {
    if (!sessionId) return;

    // Add user message immediately
    const userMessage = { role: 'user', content: message };
    setMessages((prev) => [...prev, userMessage]);

    setChatLoading(true);
    try {
      const response = await sendChatMessage(
        sessionId,
        message,
        selectedNode?.id
      );

      console.log('Chat API Response:', response);
      console.log('Has diagram update?', !!response.diagram);
      console.log('Updated diagram:', response.diagram);

      // Add assistant response
      const assistantMessage = { role: 'assistant', content: response.response };
      setMessages((prev) => [...prev, assistantMessage]);

      // Update diagram if modified
      if (response.diagram) {
        console.log('Updating diagram with new data');
        setDiagram(response.diagram);
      }

      // Update design doc if modified
      if (response.design_doc) {
        console.log('Updating design doc with new data');
        setDesignDoc(response.design_doc);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleAddNode = async (node) => {
    if (!sessionId) return;

    try {
      const updatedDiagram = await addNode(sessionId, node);
      setDiagram(updatedDiagram);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Added new node: **${node.label}** (${node.type})*`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to add node:', error);
      alert('Failed to add node. Please try again.');
    }
  };

  const handleUpdateNode = useCallback(async (updatedNodeData) => {
    if (!sessionId) return;

    try {
      const updatedDiagram = await updateNode(sessionId, updatedNodeData.id, updatedNodeData);
      setDiagram(updatedDiagram);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Updated node: **${updatedNodeData.label}***`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to update node:', error);
      alert('Failed to update node. Please try again.');
    }
  }, [sessionId]);

  const handleDeleteNode = useCallback(async (nodeId) => {
    if (!sessionId) return;

    try {
      const updatedDiagram = await deleteNode(sessionId, nodeId);
      setDiagram(updatedDiagram);

      // Clear selection if deleted node was selected
      if (selectedNode?.id === nodeId) {
        setSelectedNode(null);
      }

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Deleted node*`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to delete node:', error);
      alert('Failed to delete node. Please try again.');
    }
  }, [sessionId, selectedNode]);

  const handleAddEdge = useCallback(async (edge) => {
    if (!sessionId) return;

    try {
      const updatedDiagram = await addEdge(sessionId, edge);
      setDiagram(updatedDiagram);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Added connection between nodes*`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to add edge:', error);
      alert('Failed to add connection. Please try again.');
    }
  }, [sessionId]);

  const handleDeleteEdge = useCallback(async (edgeId) => {
    if (!sessionId) return;

    try {
      const updatedDiagram = await deleteEdge(sessionId, edgeId);
      setDiagram(updatedDiagram);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Deleted connection*`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to delete edge:', error);
      alert('Failed to delete connection. Please try again.');
    }
  }, [sessionId]);

  const handleNewDesign = () => {
    setDiagram(null);
    setSessionId(null);
    setSelectedNode(null);
    setMessages([]);
    setDesignDoc(null);
    setDesignDocOpen(false);
  };

  const handleCreateDesignDoc = async () => {
    if (!sessionId) return;

    // If design doc already exists, just reopen the panel
    if (designDoc) {
      setDesignDocOpen(true);
      return;
    }

    // Otherwise, generate a new design doc
    setDesignDocLoading(true);
    setDesignDocOpen(true); // Open panel immediately to show loading state

    try {
      // Start background generation
      const startResponse = await generateDesignDoc(sessionId);
      console.log('Design doc generation started:', startResponse);

      // Poll for completion with progress updates
      const result = await pollDesignDocStatus(
        sessionId,
        (status) => {
          // Progress callback - could update UI with elapsed time
          console.log('Generation status:', status.status,
            `(${status.elapsed_seconds?.toFixed(0) || 0}s elapsed)`);
        }
      );

      if (result.success) {
        console.log('Design doc generated successfully in', result.duration?.toFixed(1), 'seconds');
        setDesignDoc(result.design_doc);
      } else {
        throw new Error(result.error || 'Failed to generate design document');
      }
    } catch (error) {
      console.error('Failed to generate design doc:', error);
      alert('Failed to generate design document. Please try again.');
      setDesignDocOpen(false); // Close panel on error
    } finally {
      setDesignDocLoading(false);
    }
  };

  const handleSaveDesignDoc = async (content) => {
    if (!sessionId) return;

    try {
      await updateDesignDoc(sessionId, content);
      setDesignDoc(content);
    } catch (error) {
      console.error('Failed to save design doc:', error);
      throw error; // Re-throw so DesignDocPanel can handle it
    }
  };

  const handleExportDesignDoc = async (format, diagramImage) => {
    if (!sessionId) return;

    try {
      const response = await exportDesignDoc(sessionId, format, diagramImage);

      // Download files
      if (response.pdf) {
        const pdfBlob = base64ToBlob(response.pdf.content, 'application/pdf');
        downloadBlob(pdfBlob, response.pdf.filename);
      }

      if (response.markdown) {
        const mdBlob = new Blob([response.markdown.content], { type: 'text/markdown' });
        downloadBlob(mdBlob, response.markdown.filename);
      }

      if (response.diagram_png) {
        const pngBlob = base64ToBlob(response.diagram_png.content, 'image/png');
        downloadBlob(pngBlob, response.diagram_png.filename);
      }
    } catch (error) {
      console.error('Failed to export design doc:', error);
      throw error; // Re-throw so DesignDocPanel can handle it
    }
  };

  const handleCloseDesignDoc = () => {
    setDesignDocOpen(false);
  };

  const handleOpenNodePalette = (nodeType) => {
    setPreSelectedNodeType(nodeType);
    setShowAddNodeModal(true);
  };

  // Wrap setDesignDocWidth in useCallback to prevent unnecessary re-renders
  const handleDesignDocWidthChange = useCallback((width) => {
    setDesignDocWidth(width);
  }, []);

  // Wrap setChatPanelWidth in useCallback to prevent unnecessary re-renders
  const handleChatPanelWidthChange = useCallback((width) => {
    setChatPanelWidth(width);
  }, []);

  // Helper function to convert base64 to blob
  const base64ToBlob = (base64, mimeType) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  };

  // Helper function to download blob
  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Handle PNG export from floating button
  const handleExportPng = useCallback(async () => {
    const diagramElement = document.querySelector('.react-flow__viewport');
    if (!diagramElement) {
      console.error('Diagram element not found');
      return;
    }

    try {
      // Apply layout before capturing to ensure clean organization
      if (applyLayoutFn) {
        console.log('Applying layout before screenshot...');
        applyLayoutFn();
        // Wait for layout animation to complete (400ms animation + 100ms buffer)
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // Hide edge labels using opacity to avoid rendering artifacts
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

      // Convert data URL to base64 and download
      const base64 = dataUrl.split(',')[1];
      const blob = base64ToBlob(base64, 'image/png');
      downloadBlob(blob, 'diagram.png');

      console.log('Diagram PNG exported successfully');
    } catch (error) {
      console.error('Failed to export diagram:', error);
      alert('Failed to export diagram. Please try again.');
    }
  }, [applyLayoutFn, base64ToBlob, downloadBlob]);

  return (
    <div className="app">
      <header className="app-header">
        <div
          className="app-title"
          onClick={diagram ? handleNewDesign : undefined}
          style={{ cursor: diagram ? 'pointer' : 'default' }}
        >
          <div className="title-with-logo">
            <img src="/InfraSketchLogoTransparent_01.png" alt="InfraSketch Logo" className="app-logo" />
            <div className="title-text">
              <h1>InfraSketch</h1>
              <p>AI-Powered System Design Tool</p>
            </div>
          </div>
        </div>
        {diagram && (
          <div className="header-buttons">
            <button
              className="create-design-doc-button"
              onClick={handleCreateDesignDoc}
              disabled={designDocLoading}
            >
              {designDocLoading ? 'Generating...' : (designDoc && !designDocOpen ? 'Open Design Doc' : 'Create Design Doc')}
            </button>
            <button
              className="add-node-button"
              onClick={() => setShowAddNodeModal(true)}
            >
              + Add Node
            </button>
            <button
              className="new-design-button"
              onClick={handleNewDesign}
            >
              New Design
            </button>
          </div>
        )}
        <div className="auth-buttons" style={{ marginLeft: 'auto', paddingRight: '20px', display: 'flex', alignItems: 'center' }}>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="sign-in-button" style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: '1px solid rgba(255,255,255,0.2)',
                background: 'rgba(255,255,255,0.1)',
                color: 'white',
                cursor: 'pointer',
                fontSize: '14px'
              }}>
                Sign In
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: { width: 32, height: 32 }
                }
              }}
            />
          </SignedIn>
        </div>
      </header>

      <div className="app-content">
        {designDocOpen && (
          <DesignDocPanel
            designDoc={designDoc}
            onSave={handleSaveDesignDoc}
            onClose={handleCloseDesignDoc}
            sessionId={sessionId}
            onExport={handleExportDesignDoc}
            isGenerating={designDocLoading}
            onWidthChange={handleDesignDocWidthChange}
            onApplyLayout={applyLayoutFn}
          />
        )}

        <div
          className="main-area"
          style={{
            marginLeft: designDocOpen ? `${designDocWidth}px` : '0px',
            display: isMobile && (designDocOpen || selectedNode) ? 'none' : 'flex'
          }}
        >
          {!diagram && !loading && <LandingPage onGenerate={handleGenerate} loading={loading} />}
          {loading && <LoadingAnimation />}
          {diagram && (
            <DiagramCanvas
              diagram={diagram}
              loading={loading}
              onNodeClick={handleNodeClick}
              onUpdateNode={handleUpdateNode}
              onDeleteNode={handleDeleteNode}
              onAddEdge={handleAddEdge}
              onDeleteEdge={handleDeleteEdge}
              onReactFlowInit={setReactFlowInstance}
              onLayoutReady={(layoutFn) => setApplyLayoutFn(() => layoutFn)}
              onOpenNodePalette={handleOpenNodePalette}
              onExportPng={handleExportPng}
              designDocOpen={designDocOpen}
              designDocWidth={designDocWidth}
              chatPanelOpen={!!diagram}
              chatPanelWidth={chatPanelWidth}
            />
          )}
        </div>

        {diagram && (!isMobile || selectedNode) && (
          <ChatPanel
            selectedNode={selectedNode}
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={chatLoading}
            diagram={diagram}
            onWidthChange={handleChatPanelWidthChange}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>

      <AddNodeModal
        isOpen={showAddNodeModal}
        onClose={() => {
          setShowAddNodeModal(false);
          setPreSelectedNodeType(null);
        }}
        onAdd={handleAddNode}
        preSelectedType={preSelectedNodeType}
      />
    </div>
  );
}

export default App;
