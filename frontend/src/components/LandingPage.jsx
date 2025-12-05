import { useState, useEffect } from 'react';

const EXAMPLE_PROMPTS = [
  {
    title: "Video Streaming Platform",
    prompt: "Build a scalable video streaming platform with CDN, transcoding, and personalized recommendations",
    icon: "🎬"
  },
  {
    title: "E-Commerce System",
    prompt: "Design a microservices-based e-commerce platform with payment processing, inventory management, and order tracking",
    icon: "🛒"
  },
  {
    title: "Real-Time Chat App",
    prompt: "Create a real-time chat application with WebSocket connections, message queues, and presence detection",
    icon: "💬"
  },
  {
    title: "Data Analytics Pipeline",
    prompt: "Build a data analytics pipeline with stream processing, data warehousing, and real-time dashboards",
    icon: "📊"
  }
];

const FEATURES = [
  {
    icon: "🤖",
    title: "AI-Powered",
    description: "Claude AI generates professional system architecture diagrams from your descriptions"
  },
  {
    icon: "💬",
    title: "Interactive Chat",
    description: "Click any component to ask questions and request modifications in real-time"
  },
  {
    icon: "📕",
    title: "Design Documents",
    description: "Auto-generate comprehensive technical documentation with one click"
  },
  {
    icon: "📥",
    title: "Export Ready",
    description: "Download your diagrams as PNG, PDF, or Markdown files"
  }
];

const SCREENSHOTS = [
  {
    src: "/GeneratedGraph.png",
    alt: "Generated system architecture diagram",
    caption: "AI-generated architecture diagrams"
  },
  {
    src: "/FullApp_DiagramWithChat.png",
    alt: "Full application with diagram and chat",
    caption: "Complete workspace with interactive chat"
  },
  {
    src: "/FullApp_VideoWorkflowChat.png",
    alt: "Video workflow discussion",
    caption: "Deep-dive into system workflows"
  },
  {
    src: "/FullApp_DesignDocumentOpen.png",
    alt: "Design document panel",
    caption: "Auto-generated design documentation"
  },
  {
    src: "/FullApp_DesignDocWithChat.png",
    alt: "Design document with chat",
    caption: "Collaborate on your design docs"
  },
  {
    src: "/Chat_InteractWithGraph.png",
    alt: "Interactive chat with components",
    caption: "Chat with any component"
  },
  {
    src: "/Chat_InteractWithSystemDesign.png",
    alt: "Interactive system design conversation",
    caption: "Discuss your entire system design"
  },
  {
    src: "/GenerateSystemDesignDocument.png",
    alt: "Design document editor",
    caption: "Edit and export design documents"
  }
];

export default function LandingPage({ onGenerate, loading }) {
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState('claude-haiku-4-5'); // Default to Haiku (always latest)
  const [currentScreenshot, setCurrentScreenshot] = useState(0);

  // Auto-rotate screenshots every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentScreenshot((prev) => (prev + 1) % SCREENSHOTS.length);
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      onGenerate(prompt, model);
    }
  };

  const handleExampleClick = (examplePrompt) => {
    setPrompt(examplePrompt);
    // Optionally auto-submit:
    // onGenerate(examplePrompt);
  };

  const handleDotClick = (index) => {
    setCurrentScreenshot(index);
  };

  return (
    <div className="landing-page">
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Transform Ideas into System Diagrams
          </h1>
          <p className="hero-subtitle">
            Describe your system in plain English. Our AI generates professional architecture diagrams in seconds.
          </p>
          <p className="hero-cta">100% Free</p>
        </div>

        {/* Main Input Form - Front and Center */}
        <form onSubmit={handleSubmit} className="landing-input-form">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your system architecture... (e.g., Build a scalable video streaming platform with CDN, transcoding, and user recommendations)"
            disabled={loading}
            rows={4}
            className="landing-textarea"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="landing-generate-button"
          >
            {loading ? 'Generating...' : 'Generate System Design'}
          </button>

          {/* Model selector below button */}
          <div style={{ marginTop: '12px', marginBottom: '-20px', textAlign: 'center' }}>
            <select
              id="model-select-landing"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={loading}
              style={{
                padding: '6px 10px',
                fontSize: '13px',
                borderRadius: '6px',
                border: '1px solid #ddd',
                backgroundColor: 'white',
                cursor: loading ? 'not-allowed' : 'pointer',
                outline: 'none',
                color: '#666'
              }}
            >
              <option value="claude-haiku-4-5">Haiku 4.5</option>
              <option value="claude-sonnet-4-5">Sonnet 4.5</option>
            </select>
          </div>
        </form>

        {/* Example Prompts */}
        <div className="example-prompts-section">
          <p className="example-prompts-label">Or try an example:</p>
          <div className="example-prompts-grid">
            {EXAMPLE_PROMPTS.map((example, index) => (
              <button
                key={index}
                onClick={() => handleExampleClick(example.prompt)}
                className="example-prompt-card"
                disabled={loading}
              >
                <span className="example-icon">{example.icon}</span>
                <span className="example-title">{example.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="features-section">
        <h2 className="features-heading">Powerful Features</h2>
        <div className="features-grid">
          {FEATURES.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Screenshots Showcase - Carousel */}
      <div className="showcase-section">
        <h2 className="showcase-heading">See It In Action</h2>
        <div className="showcase-carousel">
          <div className="carousel-container">
            <div
              className="carousel-track"
              style={{
                transform: `translateX(-${currentScreenshot * 100}%)`
              }}
            >
              {SCREENSHOTS.map((screenshot, index) => (
                <div key={index} className="carousel-slide">
                  <img
                    src={screenshot.src}
                    alt={screenshot.alt}
                    className="carousel-image"
                  />
                  <p className="carousel-caption">{screenshot.caption}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Navigation Dots */}
          <div className="carousel-dots">
            {SCREENSHOTS.map((_, index) => (
              <button
                key={index}
                onClick={() => handleDotClick(index)}
                className={`carousel-dot ${index === currentScreenshot ? 'active' : ''}`}
                aria-label={`View screenshot ${index + 1}`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="how-it-works-section">
        <h2 className="how-it-works-heading">How It Works</h2>
        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">Describe Your System</h3>
            <p className="step-description">
              Write a simple description of your architecture in plain English
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">AI Generates Diagram</h3>
            <p className="step-description">
              Claude AI creates a professional architecture diagram with all components
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Refine & Export</h3>
            <p className="step-description">
              Chat to make changes, generate docs, and export in your preferred format
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">AI-powered system architecture design</p>
          </div>
          <div className="footer-links">
            <a href="/about">About</a>
            <a href="/blog">Blog</a>
            <a href="/careers">Careers</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
            <a href="/contact">Contact</a>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2025 InfraSketch. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
