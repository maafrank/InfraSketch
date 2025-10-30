import { useState } from 'react';
import InputPanel from './components/InputPanel';
import DiagramCanvas from './components/DiagramCanvas';
import ChatPanel from './components/ChatPanel';
import AddNodeModal from './components/AddNodeModal';
import ExportButton from './components/ExportButton';
import { generateDiagram, sendChatMessage, addNode, deleteNode, updateNode, addEdge, deleteEdge } from './api/client';
import './App.css';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [diagram, setDiagram] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [showAddNodeModal, setShowAddNodeModal] = useState(false);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  const handleGenerate = async (prompt) => {
    setLoading(true);
    try {
      const response = await generateDiagram(prompt);
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

      setMessages([{ role: 'assistant', content: summary }]);
    } catch (error) {
      console.error('Failed to generate diagram:', error);
      alert('Failed to generate diagram. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node) => {
    // Only add context message if selecting a different node
    if (selectedNode?.id !== node.id) {
      const contextMessage = {
        role: 'system',
        content: `*Now focusing on: **${node.data.label}** (${node.data.type})*`,
      };
      setMessages((prev) => [...prev, contextMessage]);
    }
    setSelectedNode(node);
  };

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

  const handleUpdateNode = async (updatedNodeData) => {
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
  };

  const handleDeleteNode = async (nodeId) => {
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
  };

  const handleAddEdge = async (edge) => {
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
  };

  const handleDeleteEdge = async (edgeId) => {
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
  };

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>InfraSketch</h1>
          <p>AI-Powered System Design Tool</p>
        </div>
        {diagram && (
          <div className="header-buttons">
            <ExportButton sessionId={sessionId} reactFlowInstance={reactFlowInstance} />
            <button
              className="add-node-button"
              onClick={() => setShowAddNodeModal(true)}
            >
              + Add Node
            </button>
            <button
              className="new-design-button"
              onClick={() => {
                setDiagram(null);
                setSessionId(null);
                setSelectedNode(null);
                setMessages([]);
              }}
            >
              New Design
            </button>
          </div>
        )}
      </header>

      <div className="app-content">
        <div className="main-area">
          {!diagram && <InputPanel onGenerate={handleGenerate} loading={loading} />}
          <DiagramCanvas
            diagram={diagram}
            onNodeClick={handleNodeClick}
            onUpdateNode={handleUpdateNode}
            onDeleteNode={handleDeleteNode}
            onAddEdge={handleAddEdge}
            onDeleteEdge={handleDeleteEdge}
            onReactFlowInit={setReactFlowInstance}
          />
        </div>

        {diagram && (
          <ChatPanel
            selectedNode={selectedNode}
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={chatLoading}
            diagram={diagram}
          />
        )}
      </div>

      <AddNodeModal
        isOpen={showAddNodeModal}
        onClose={() => setShowAddNodeModal(false)}
        onAdd={handleAddNode}
      />
    </div>
  );
}

export default App;
