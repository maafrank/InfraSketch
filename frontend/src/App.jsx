import { useState } from 'react';
import InputPanel from './components/InputPanel';
import DiagramCanvas from './components/DiagramCanvas';
import ChatPanel from './components/ChatPanel';
import { generateDiagram, sendChatMessage } from './api/client';
import './App.css';

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [diagram, setDiagram] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

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
      setMessages([]);
      setSelectedNode(null);
    } catch (error) {
      console.error('Failed to generate diagram:', error);
      alert('Failed to generate diagram. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
    // Don't reset messages - keep conversation history
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

  const handleCloseChat = () => {
    setSelectedNode(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>InfraSketch</h1>
        <p>AI-Powered System Design Tool</p>
      </header>

      <div className="app-content">
        <div className="main-area">
          {!diagram && <InputPanel onGenerate={handleGenerate} loading={loading} />}
          <DiagramCanvas diagram={diagram} onNodeClick={handleNodeClick} />
        </div>

        {selectedNode && (
          <ChatPanel
            selectedNode={selectedNode}
            messages={messages}
            onSendMessage={handleSendMessage}
            onClose={handleCloseChat}
            loading={chatLoading}
          />
        )}
      </div>

      {diagram && (
        <div className="reset-button-container">
          <button
            className="reset-button"
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
    </div>
  );
}

export default App;
