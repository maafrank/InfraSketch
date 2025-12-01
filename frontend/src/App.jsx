import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth, useClerk } from "@clerk/clerk-react";
import { toPng } from 'html-to-image';
import { useTheme } from './contexts/ThemeContext';
import LandingPage from './components/LandingPage';
import DiagramCanvas from './components/DiagramCanvas';
import ChatPanel from './components/ChatPanel';
import DesignDocPanel from './components/DesignDocPanel';
import AddNodeModal from './components/AddNodeModal';
import SessionHistorySidebar from './components/SessionHistorySidebar';
import NodePalette from './components/NodePalette';
import ThemeToggle from './components/ThemeToggle';
import {
  generateDiagram,
  pollDiagramStatus,
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
  setClerkTokenGetter,
  getSession,
  createBlankSession,
  pollSessionName,
  createNodeGroup,
  generateNodeDescription,
  toggleGroupCollapse,
  ungroupNodes
} from './api/client';
import './App.css';

function App({ resumeMode = false }) {
  const { theme } = useTheme();
  const [sessionId, setSessionId] = useState(null);
  const [sessionName, setSessionName] = useState(null);
  const [diagram, setDiagram] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [loadingStepText, setLoadingStepText] = useState('');
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
  const [examplePrompt, setExamplePrompt] = useState(null);
  const [currentModel, setCurrentModel] = useState('claude-haiku-4-5'); // Track current model

  // Session history sidebar state
  const [sessionHistoryOpen, setSessionHistoryOpen] = useState(false);
  const [sessionHistorySidebarWidth, setSessionHistorySidebarWidth] = useState(300);

  // Node palette state
  const [nodePaletteOpen, setNodePaletteOpen] = useState(false);

  // Layout direction state
  const [layoutDirection, setLayoutDirection] = useState('TB'); // 'TB' (top-bottom) or 'LR' (left-right)

  // Mobile detection
  const [isMobile, setIsMobile] = useState(false);

  // Node merging state
  const [mergingNodes, setMergingNodes] = useState(false);

  // Auth - Set up token getter for API client
  const { getToken, isSignedIn } = useAuth();
  const { openSignIn } = useClerk();

  // Routing
  const { sessionId: urlSessionId } = useParams();
  const navigate = useNavigate();

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

  // Re-center diagram when sidebar opens/closes
  useEffect(() => {
    if (diagram && applyLayoutFn && !isMobile) {
      // Small delay to allow panel animations to complete
      const timer = setTimeout(() => {
        applyLayoutFn();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [sessionHistoryOpen, sessionHistorySidebarWidth, diagram, applyLayoutFn, isMobile]);

  // Resume session from URL parameter
  useEffect(() => {
    if (resumeMode && urlSessionId && !sessionId && isSignedIn) {
      loadSession(urlSessionId);
    }
  }, [resumeMode, urlSessionId, sessionId, isSignedIn]);

  const loadSession = async (sid) => {
    setLoading(true);
    try {
      const sessionData = await getSession(sid);

      // Restore full session state
      setSessionId(sessionData.session_id);
      setSessionName(sessionData.name);
      setDiagram(sessionData.diagram);
      setMessages(sessionData.messages || []);
      setDesignDoc(sessionData.design_doc);

      // Restore model from session (fallback to default if not present)
      if (sessionData.model) {
        setCurrentModel(sessionData.model);
      }

      // Always close design doc panel when switching sessions
      // Users can reopen it if they want to view the design doc
      setDesignDocOpen(false);

      console.log('Session loaded:', sessionData.session_id, 'Name:', sessionData.name);
    } catch (error) {
      console.error('Failed to load session:', error);
      alert('Failed to load session. It may have expired or you may not have access.');
      navigate('/');
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

  const handleExitNodeFocus = useCallback(() => {
    const contextMessage = {
      role: 'system',
      content: `*Returned to system chat*`,
    };
    setMessages((prev) => [...prev, contextMessage]);
    setSelectedNode(null);
  }, []);

  const handleSendMessage = async (message) => {
    // Check if user is signed in, redirect to sign-in if not
    if (!isSignedIn) {
      openSignIn();
      return;
    }

    // If diagram has no nodes, this is initial generation - use generate endpoint
    const hasNodes = diagram?.nodes?.length > 0;
    if (!hasNodes) {
      setLoading(true);

      // Add user message immediately
      const userMessage = { role: 'user', content: message };
      setMessages([userMessage]);

      // Define loading steps (without emojis)
      const loadingSteps = [
        'Analyzing your architecture...',
        'Designing system components...',
        'Mapping connections and data flow...',
        'Optimizing component placement...',
        'Generating visual layout...',
        'Finalizing your diagram...'
      ];

      // Update loading step text progressively
      const updateLoadingSteps = async () => {
        for (let i = 0; i < loadingSteps.length; i++) {
          setLoadingStepText(loadingSteps[i]);

          // Wait 2-3 seconds before showing next step
          if (i < loadingSteps.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 2500));
          }
        }
      };

      // Start updating loading steps (runs in background)
      const loadingStepsPromise = updateLoadingSteps();

      try {
        // Start async diagram generation (returns immediately with session_id)
        const response = await generateDiagram(message, currentModel);
        const newSessionId = response.session_id;
        setSessionId(newSessionId);

        console.log('Started diagram generation, polling for completion...', newSessionId);

        // Poll for completion (loading steps continue cycling naturally)
        const result = await pollDiagramStatus(newSessionId, (status) => {
          // Log progress for debugging
          if (status.elapsed_seconds) {
            console.log(`Diagram generation: ${status.status} (${status.elapsed_seconds.toFixed(1)}s)`);
          }
        });

        // Wait for loading steps animation to finish
        await loadingStepsPromise;

        if (result.success) {
          setDiagram(result.diagram);
          setMessages(result.messages || []);
          if (result.name) {
            setSessionName(result.name);
          }
          console.log('Generated initial diagram:', result);
        } else {
          throw new Error(result.error || 'Failed to generate diagram');
        }

        // Clear loading step text
        setLoadingStepText('');

      } catch (error) {
        console.error('Failed to generate diagram:', error);

        // Provide specific error messages based on error type
        let errorMessage = 'Failed to generate diagram. Please try again.';

        if (error.message?.includes('timed out')) {
          errorMessage = 'Diagram generation timed out after 5 minutes. Try:\n\n1. Simplify your prompt\n2. Use Haiku 4.5 (faster)\n3. Try again in a moment';
        } else if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          errorMessage = 'Request timed out. Please try again.';
        } else if (!error.response && error.message) {
          errorMessage = error.message;
        } else if (error.response?.status >= 500) {
          errorMessage = `Server error (${error.response.status}). Please try again in a moment.`;
        }

        alert(errorMessage);
      } finally {
        setLoading(false);
        setLoadingStepText('');
      }
      return;
    }

    // Auto-create session if it doesn't exist (for chat on blank canvas)
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        const newSession = await createBlankSession();
        currentSessionId = newSession.session_id;
        setSessionId(currentSessionId);
        setDiagram(newSession.diagram);
        console.log('Auto-created blank session:', currentSessionId);
      } catch (error) {
        console.error('Failed to create session:', error);
        alert('Failed to create session. Please try again.');
        return;
      }
    }

    // Add user message immediately
    const userMessage = { role: 'user', content: message };
    setMessages((prev) => [...prev, userMessage]);

    setChatLoading(true);
    try {
      const response = await sendChatMessage(
        currentSessionId,
        message,
        selectedNode?.id,
        currentModel
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

      // Poll for session name if this was the first message (no session name yet)
      if (!sessionName || sessionName === 'Untitled Design') {
        pollSessionName(currentSessionId, (name) => {
          console.log('Session name updated after chat:', name);
          setSessionName(name);
        }).catch(error => {
          console.error('Failed to poll session name:', error);
        });
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
    // Auto-create session if it doesn't exist
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        const newSession = await createBlankSession();
        currentSessionId = newSession.session_id;
        setSessionId(currentSessionId);
        setDiagram(newSession.diagram);
        console.log('Auto-created blank session:', currentSessionId);
      } catch (error) {
        console.error('Failed to create session:', error);
        alert('Failed to create session. Please try again.');
        return;
      }
    }

    try {
      const updatedDiagram = await addNode(currentSessionId, node);
      setDiagram(updatedDiagram);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Added new node: **${node.label}** (${node.type})*`,
      };
      setMessages((prev) => [...prev, systemMessage]);

      // Poll for session name if we just added the 5th node and no name yet
      if (updatedDiagram.nodes.length === 5 && (!sessionName || sessionName === 'Untitled Design')) {
        pollSessionName(currentSessionId, (name) => {
          console.log('Session name updated after adding 5th node:', name);
          setSessionName(name);
        }).catch(error => {
          console.error('Failed to poll session name:', error);
        });
      }
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

  const handleMergeNodes = useCallback(async (draggedNodeId, targetNodeId) => {
    if (!sessionId) return;

    setMergingNodes(true);
    try {
      console.log('Merging nodes:', draggedNodeId, 'into', targetNodeId);

      // Call with AI generation enabled (default: true)
      const response = await createNodeGroup(sessionId, [draggedNodeId, targetNodeId], true);
      setDiagram(response.diagram);

      // Find the created group node to get its AI-generated label
      const groupNode = response.diagram.nodes.find(n => n.id === response.group_id);
      const groupLabel = groupNode ? groupNode.label : 'collapsible group';

      // Add system message to chat with AI-generated label
      const systemMessage = {
        role: 'system',
        content: `*Merged nodes into "${groupLabel}" (AI-generated)*`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to merge nodes:', error);
      alert('Failed to merge nodes. Please try again.');
    } finally {
      setMergingNodes(false);
    }
  }, [sessionId]);

  const handleUngroupNodes = useCallback(async (groupId) => {
    if (!sessionId) return;

    try {
      console.log('Ungrouping:', groupId);
      const response = await ungroupNodes(sessionId, groupId);
      setDiagram(response);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Ungrouped nodes from group*`,
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error('Failed to ungroup nodes:', error);
      alert('Failed to ungroup nodes. Please try again.');
    }
  }, [sessionId]);

  const handleRegenerateDescription = useCallback(async (nodeId) => {
    if (!sessionId) return;

    try {
      console.log('Regenerating AI description for node:', nodeId);
      const response = await generateNodeDescription(sessionId, nodeId);

      // Update diagram with new description
      setDiagram(response.diagram);

      // Add system message to chat
      const systemMessage = {
        role: 'system',
        content: `*Regenerated description for "${response.label}" using AI*`,
      };
      setMessages((prev) => [...prev, systemMessage]);

      return response; // Return the response for the tooltip to use
    } catch (error) {
      console.error('Failed to regenerate description:', error);
      throw error; // Re-throw so tooltip can handle it
    }
  }, [sessionId]);

  const handleToggleGroupCollapse = useCallback(async (groupId) => {
    if (!sessionId) return;

    try {
      const updatedDiagram = await toggleGroupCollapse(sessionId, groupId);
      setDiagram(updatedDiagram);
    } catch (error) {
      console.error('Failed to toggle group collapse:', error);
      alert('Failed to toggle group. Please try again.');
    }
  }, [sessionId]);

  // Helper function to check if current session is pristine (empty)
  const isSessionPristine = useCallback(() => {
    const hasNodes = diagram?.nodes?.length > 0;
    const hasEdges = diagram?.edges?.length > 0;
    const hasMessages = messages.length > 0;
    const hasDesignDoc = !!designDoc;

    return !hasNodes && !hasEdges && !hasMessages && !hasDesignDoc;
  }, [diagram, messages, designDoc]);

  const handleNewDesign = () => {
    // Just reset local state - session will be created when user generates content
    setSessionId(null);
    setDiagram(null);
    setSelectedNode(null);
    setMessages([]);
    setDesignDoc(null);
    setDesignDocOpen(false);
    setSessionName('Untitled Design');
    navigate('/');
    console.log('Reset to new design state');
  };

  const handleSessionDeleted = useCallback((deletedSessionId) => {
    console.log('Current session was deleted:', deletedSessionId);

    // Close the session history sidebar
    setSessionHistoryOpen(false);

    // Reset to fresh state - session will be created when user generates content
    setSessionId(null);
    setDiagram(null);
    setSelectedNode(null);
    setMessages([]);
    setDesignDoc(null);
    setDesignDocOpen(false);
    setSessionName('Untitled Design');
    navigate('/');
  }, [navigate]);

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
    // Always open the AddNodeModal, just like the "+ Add Node" button
    setPreSelectedNodeType(nodeType || null);
    setShowAddNodeModal(true);
  };

  const handleSelectNodeType = (nodeType) => {
    setPreSelectedNodeType(nodeType);
    setShowAddNodeModal(true);
    setNodePaletteOpen(false);
  };

  // Wrap setDesignDocWidth in useCallback to prevent unnecessary re-renders
  const handleDesignDocWidthChange = useCallback((width) => {
    setDesignDocWidth(width);
  }, []);

  // Wrap setChatPanelWidth in useCallback to prevent unnecessary re-renders
  const handleChatPanelWidthChange = useCallback((width) => {
    setChatPanelWidth(width);
  }, []);

  // Wrap setSessionHistorySidebarWidth in useCallback to prevent unnecessary re-renders
  const handleSessionHistorySidebarWidthChange = useCallback((width) => {
    setSessionHistorySidebarWidth(width);
  }, []);

  // Handler for loading a session from history
  const handleLoadSession = useCallback(async (sessionId) => {
    await loadSession(sessionId);
  }, []);

  // Handler for example prompt click
  const handleExampleClick = useCallback((prompt) => {
    setExamplePrompt(prompt);
    // Reset after a brief delay to allow the effect to trigger
    setTimeout(() => setExamplePrompt(null), 100);
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
          onClick={isSignedIn ? handleNewDesign : undefined}
          style={{ cursor: isSignedIn ? 'pointer' : 'default' }}
        >
          <div className="title-with-logo">
            <img
              src={theme === 'dark' ? "/InfraSketchLogoTransparent_02.png" : "/InfraSketchLogoTransparent_01.png"}
              alt="InfraSketch Logo"
              className="app-logo"
            />
            <div className="title-text">
              <h1>InfraSketch</h1>
              <p>AI-Powered System Design Tool</p>
            </div>
          </div>
        </div>
        <div className="header-right">
          <div className="header-buttons">
            {isSignedIn && (
              <>
                <button
                  className={`history-toggle-button ${sessionHistoryOpen ? 'active' : ''}`}
                  onClick={() => setSessionHistoryOpen(!sessionHistoryOpen)}
                  title={sessionHistoryOpen ? 'Close history' : 'Open history'}
                  aria-label={sessionHistoryOpen ? 'Close session history' : 'Open session history'}
                  aria-expanded={sessionHistoryOpen}
                >
                  {sessionHistoryOpen ? '✕' : '☰'}
                </button>
                <button
                  className="create-design-doc-button"
                  onClick={handleCreateDesignDoc}
                  disabled={designDocLoading || !diagram}
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
              </>
            )}
          </div>
          <div className="auth-buttons">
            <ThemeToggle />
            <SignedOut>
              <SignInButton mode="modal">
                <button className="sign-in-button">
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
        </div>
      </header>

      <div className="app-content">
        {sessionHistoryOpen && (
          <SessionHistorySidebar
            isOpen={sessionHistoryOpen}
            onClose={() => setSessionHistoryOpen(false)}
            onSessionSelect={handleLoadSession}
            onWidthChange={handleSessionHistorySidebarWidthChange}
            currentSessionId={sessionId}
            sessionNameUpdated={sessionName}
            onSessionDeleted={handleSessionDeleted}
          />
        )}

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
            sessionHistorySidebarWidth={sessionHistoryOpen ? sessionHistorySidebarWidth : 0}
          />
        )}

        <div
          className="main-area"
          style={{
            marginLeft: isSignedIn ? `${(sessionHistoryOpen ? sessionHistorySidebarWidth : 0) + (designDocOpen ? designDocWidth : 0)}px` : '0px',
            display: isMobile && (sessionHistoryOpen || designDocOpen || selectedNode) ? 'none' : 'flex'
          }}
        >
          {!isSignedIn && <LandingPage onGenerate={handleSendMessage} loading={loading} />}
          {isSignedIn && (
            <DiagramCanvas
              diagram={diagram}
              loading={loading}
              onNodeClick={handleNodeClick}
              onUpdateNode={handleUpdateNode}
              onDeleteNode={handleDeleteNode}
              onAddEdge={handleAddEdge}
              onDeleteEdge={handleDeleteEdge}
              onMergeNodes={handleMergeNodes}
              onUngroupNodes={handleUngroupNodes}
              onToggleCollapse={handleToggleGroupCollapse}
              onRegenerateDescription={handleRegenerateDescription}
              onReactFlowInit={setReactFlowInstance}
              onLayoutReady={(layoutFn) => setApplyLayoutFn(() => layoutFn)}
              onOpenNodePalette={handleOpenNodePalette}
              onExportPng={handleExportPng}
              onExampleClick={handleExampleClick}
              designDocOpen={designDocOpen}
              designDocWidth={designDocWidth}
              chatPanelOpen={true}
              chatPanelWidth={chatPanelWidth}
              layoutDirection={layoutDirection}
              onLayoutDirectionChange={setLayoutDirection}
              mergingNodes={mergingNodes}
            />
          )}
        </div>

        {isSignedIn && (!isMobile || selectedNode) && (
          <ChatPanel
            selectedNode={selectedNode}
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={chatLoading}
            loadingStepText={loadingStepText}
            diagram={diagram}
            onWidthChange={handleChatPanelWidthChange}
            onClose={() => setSelectedNode(null)}
            onExitNodeFocus={handleExitNodeFocus}
            examplePrompt={examplePrompt}
            currentModel={currentModel}
            onModelChange={setCurrentModel}
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

      {isSignedIn && (
        <NodePalette
          isOpen={nodePaletteOpen}
          onClose={() => setNodePaletteOpen(false)}
          onSelectType={handleSelectNodeType}
          designDocOpen={designDocOpen}
          designDocWidth={designDocWidth}
          chatPanelOpen={!!diagram}
          chatPanelWidth={chatPanelWidth}
          sessionHistoryOpen={sessionHistoryOpen}
          sessionHistorySidebarWidth={sessionHistorySidebarWidth}
        />
      )}
    </div>
  );
}

export default App;
