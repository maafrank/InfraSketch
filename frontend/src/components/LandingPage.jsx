import { useState, useEffect } from 'react';

const EXAMPLE_PROMPTS = [
  {
    title: "Twitter Timeline",
    prompt: "Design Twitter's home timeline with feed generation, caching, and real-time updates",
    icon: "🐦"
  },
  {
    title: "E-Commerce Checkout",
    prompt: "Design a scalable e-commerce checkout flow with cart, payments, and inventory",
    icon: "🛒"
  },
  {
    title: "URL Shortener",
    prompt: "Design a URL shortening service like bit.ly with analytics and high availability",
    icon: "🔗"
  },
  {
    title: "Video Streaming",
    prompt: "Design a video streaming platform like YouTube with upload, transcoding, and CDN",
    icon: "📺"
  }
];

const FEATURES = [
  {
    icon: "🎯",
    title: "Real Practice",
    description: "Design systems the way interviews actually work, not static diagrams"
  },
  {
    icon: "💬",
    title: "Iterate Like an Interview",
    description: "Ask 'what if traffic spikes 10x?' and watch your design evolve"
  },
  {
    icon: "🧠",
    title: "Learn the Why",
    description: "Click any component to understand why it exists in your design"
  },
  {
    icon: "📄",
    title: "Interview-Ready Docs",
    description: "Export architecture summaries, tradeoffs, and component details"
  }
];

const LAUNCH_BADGES = [
  {
    name: "Product Hunt",
    href: "https://www.producthunt.com/products/infrasketch-2?embed=true&utm_source=badge-featured&utm_medium=badge&utm_campaign=badge-infrasketch-2",
    imgSrc: "https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1053327&theme=light&t=1767037203955",
    alt: "InfraSketch - Agent-Powered System Design | Product Hunt",
    width: 250,
    height: 54
  },
  {
    name: "FoundrList",
    href: "https://foundrlist.com/product/infrasketch-2",
    imgSrc: "https://foundrlist.com/api/badge/infrasketch-2",
    alt: "Live on FoundrList",
    width: 168,
    height: 64
  },
  {
    name: "SaaSHub",
    href: "https://www.saashub.com/infrasketch-net?utm_source=badge&utm_campaign=badge&utm_content=infrasketch-net&badge_variant=color&badge_kind=approved",
    imgSrc: "https://cdn-b.saashub.com/img/badges/approved-color.png?v=1",
    alt: "InfraSketch.net badge",
    width: 150,
    height: null
  },
  {
    name: "TinyLaunch",
    href: "https://tinylaunch.com",
    imgSrc: "https://tinylaunch.com/tinylaunch_badge_launching_soon.svg",
    alt: "TinyLaunch Badge",
    width: 202,
    height: null
  },
  {
    name: "PeerPush",
    href: "https://peerpush.net/p/infrasketch",
    imgSrc: "https://peerpush.net/p/infrasketch/badge.png",
    alt: "InfraSketch badge",
    width: 230,
    height: null
  },
  {
    name: "TryLaunch",
    href: "https://trylaunch.ai/launch/infrasketch",
    imgSrc: "https://trylaunch.ai/launch-icon-light.png",
    alt: "Live on Launch",
    width: 20,
    height: 20,
    customStyle: true
  }
];

const SCREENSHOTS = [
  {
    src: "/full-app-with-design-doc.png",
    alt: "Full application with session history, design doc, and diagram",
    caption: "Complete workspace with session history"
  },
  {
    src: "/tutorial.png",
    alt: "Interactive tutorial showing 3 steps to get started",
    caption: "Interactive tutorial guides you through the basics"
  },
  {
    src: "/followup-questions.png",
    alt: "AI-suggested follow-up questions after diagram generation",
    caption: "Smart suggestions help you iterate on your design"
  },
  {
    src: "/analytics-diagram-generated.png",
    alt: "Generated analytics architecture diagram",
    caption: "Agent-generated architecture diagrams"
  },
  {
    src: "/ecommerce-collapsed-groups.png",
    alt: "E-commerce diagram with collapsed component groups",
    caption: "Organize components into collapsible groups"
  },
  {
    src: "/ecommerce-expanded.png",
    alt: "E-commerce diagram with expanded groups",
    caption: "Expand groups to see all components"
  },
  {
    src: "/email-platform-model-selector.png",
    alt: "Email platform with model selector",
    caption: "Choose between Haiku and Sonnet models"
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
            Practice System Design Interviews by Actually Designing Systems
          </h1>
          <p className="hero-subtitle">
            Stop memorizing diagrams. Start building real architectures. Describe a system, watch it appear, ask "what if?" and iterate like a real interview.
          </p>
          <p className="hero-cta">No drag-and-drop. No blank canvas paralysis. Just design.</p>
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

      {/* The Problem Section */}
      <div className="problem-section">
        <h2 className="problem-heading">The Problem</h2>
        <p className="problem-lead">
          System design interviews are brutal for one reason: you're expected to design real systems, but most learning tools only explain them.
        </p>
        <ul className="problem-list">
          <li>Blog posts show static diagrams</li>
          <li>Whiteboards punish hesitation</li>
          <li>Diagram tools slow you down</li>
          <li>AI chatbots talk but cannot build</li>
        </ul>
        <p className="problem-conclusion">
          You know the concepts. You struggle to turn them into architecture under pressure.
        </p>
      </div>

      {/* Features Section */}
      <div className="features-section">
        <h2 className="features-heading">The Solution</h2>
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
            <h3 className="step-title">Describe the System</h3>
            <p className="step-description">
              "Design Twitter's timeline" or "Design a URL shortener"
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">Watch It Appear</h3>
            <p className="step-description">
              Services, databases, caches, queues in a clean, readable layout
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Iterate & Learn</h3>
            <p className="step-description">
              Ask questions like an interviewer would, get explanations tied to your design
            </p>
          </div>
        </div>
      </div>

      {/* Featured On Section */}
      <div className="featured-on-section">
        <h2 className="featured-on-heading">Featured On</h2>
        <div className="featured-on-grid">
          {/* Product Hunt */}
          <a
            href="https://www.producthunt.com/products/infrasketch-2?embed=true&utm_source=badge-featured&utm_medium=badge&utm_campaign=badge-infrasketch-2"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1053327&theme=light"
              alt="InfraSketch - Product Hunt"
              className="featured-badge-img"
              width="250"
              height="54"
            />
          </a>

          {/* FoundrList */}
          <a
            href="https://foundrlist.com/product/infrasketch-2"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://foundrlist.com/api/badge/infrasketch-2"
              alt="Live on FoundrList"
              className="featured-badge-img"
              width="168"
              height="64"
            />
          </a>

          {/* SaaSHub */}
          <a
            href="https://www.saashub.com/infrasketch-net?utm_source=badge&utm_campaign=badge&utm_content=infrasketch-net&badge_variant=color&badge_kind=approved"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://cdn-b.saashub.com/img/badges/approved-color.png?v=1"
              alt="SaaSHub Approved"
              className="featured-badge-img"
            />
          </a>

          {/* TinyLaunch */}
          <a
            href="https://tinylaunch.com"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://tinylaunch.com/tinylaunch_badge_launching_soon.svg"
              alt="TinyLaunch Badge"
              className="featured-badge-img"
              width="202"
            />
          </a>

          {/* PeerPush */}
          <a
            href="https://peerpush.net/p/infrasketch"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://peerpush.net/p/infrasketch/badge.png"
              alt="InfraSketch on PeerPush"
              className="featured-badge-img"
              width="230"
            />
          </a>

          {/* TryLaunch */}
          <a
            href="https://trylaunch.ai/launch/infrasketch"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link featured-badge-styled"
          >
            <img
              src="https://trylaunch.ai/launch-icon-light.png"
              alt="Launch"
              width="20"
              height="20"
            />
            <span>Live on Launch</span>
          </a>
        </div>
      </div>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">Agent-powered system architecture design</p>
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
