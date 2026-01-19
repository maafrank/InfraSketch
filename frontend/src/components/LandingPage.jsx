import { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useScrollAnimation, useStaggeredAnimation } from '../hooks/useScrollAnimation';
import { Twitter, ShoppingCart, Link, Tv, Pencil, MessageSquare, Brain, FileText } from 'lucide-react';

const EXAMPLE_PROMPTS = [
  {
    title: "Twitter Timeline",
    prompt: "Design Twitter's home timeline with feed generation, caching, and real-time updates",
    icon: Twitter
  },
  {
    title: "E-Commerce Checkout",
    prompt: "Design a scalable e-commerce checkout flow with cart, payments, and inventory",
    icon: ShoppingCart
  },
  {
    title: "URL Shortener",
    prompt: "Design a URL shortening service like bit.ly with analytics and high availability",
    icon: Link
  },
  {
    title: "Video Streaming",
    prompt: "Design a video streaming platform like YouTube with upload, transcoding, and CDN",
    icon: Tv
  }
];

const FEATURES = [
  {
    icon: Pencil,
    title: "Describe, Don't Draw",
    description: "Tell our AI agent what you want to build. Watch your architecture appear in seconds."
  },
  {
    icon: MessageSquare,
    title: "Chat to Iterate",
    description: "Ask 'what if we need 10x scale?' or 'add a cache layer' and watch your design evolve."
  },
  {
    icon: Brain,
    title: "Understand Every Component",
    description: "Click any component to ask why it exists, explore tradeoffs, or consider alternatives."
  },
  {
    icon: FileText,
    title: "Export & Build",
    description: "Generate a design doc with architecture diagrams, component details, and implementation notes."
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
    src: "/url-shortener-prompt-input.png",
    alt: "Entering a prompt to design a URL shortening service",
    caption: "Describe your system in natural language"
  },
  {
    src: "/url-shortener-diagram-generated.png",
    alt: "Generated URL shortener architecture diagram",
    caption: "AI generates a complete architecture diagram"
  },
  {
    src: "/url-shortener-chat-add-loadbalancer.png",
    alt: "Chat message requesting to add a load balancer",
    caption: "Refine your design through conversation"
  },
  {
    src: "/url-shortener-diagram-with-loadbalancer.png",
    alt: "Updated diagram with load balancer added",
    caption: "Watch your diagram update in real-time"
  },
  {
    src: "/url-shortener-design-doc-panel.png",
    alt: "Generated system design document",
    caption: "Generate comprehensive design documentation"
  },
  {
    src: "/url-shortener-full-app-view.png",
    alt: "Full application view with diagram, chat, and design doc",
    caption: "Complete workspace with all panels"
  },
  {
    src: "/full-app-with-design-doc.png",
    alt: "Full application with session history, design doc, and diagram",
    caption: "Manage multiple designs with session history"
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

  // Scroll animations for sections
  const problemAnimation = useScrollAnimation();
  const featuresAnimation = useScrollAnimation();
  const showcaseAnimation = useScrollAnimation();
  const howItWorksAnimation = useScrollAnimation();
  const featuredOnAnimation = useScrollAnimation();

  // Staggered animations for cards
  const featureCards = useStaggeredAnimation(FEATURES.length, { staggerDelay: 100 });
  const stepCards = useStaggeredAnimation(3, { staggerDelay: 150 });

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

  // Structured data for SEO
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "name": "InfraSketch",
        "description": "AI-powered system design tool that generates architecture diagrams from natural language descriptions. Create AWS, microservices, and cloud architecture diagrams in seconds.",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "USD",
          "description": "Free tier with 25 credits per month"
        },
        "featureList": [
          "Natural language to architecture diagram generation",
          "AI-powered conversational design refinement",
          "Auto-generated technical design documents",
          "Export to PNG, PDF, or Markdown",
          "Session history and collaboration",
          "Multiple AI model options (Haiku, Sonnet)",
          "Collapsible component grouping"
        ],
        "screenshot": "https://infrasketch.net/full-app-with-design-doc.png"
      },
      {
        "@type": "HowTo",
        "name": "How to Create AI Architecture Diagrams with InfraSketch",
        "description": "Generate professional system architecture diagrams using AI in 3 simple steps",
        "totalTime": "PT2M",
        "tool": {
          "@type": "HowToTool",
          "name": "InfraSketch"
        },
        "step": [
          {
            "@type": "HowToStep",
            "position": 1,
            "name": "Describe Your System",
            "text": "Tell the AI what you want to build in plain English. No templates, no drag-and-drop, just describe it.",
            "url": "https://infrasketch.net/#step1"
          },
          {
            "@type": "HowToStep",
            "position": 2,
            "name": "Generate & Iterate",
            "text": "Watch your architecture appear in seconds. Ask questions, request changes, and refine your design through conversation.",
            "url": "https://infrasketch.net/#step2"
          },
          {
            "@type": "HowToStep",
            "position": 3,
            "name": "Export & Build",
            "text": "Generate a comprehensive design doc with architecture diagrams, component details, and implementation notes. Then start building.",
            "url": "https://infrasketch.net/#step3"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page">
      <Helmet>
        <title>AI System Design Tool | Architecture Diagram Generator | InfraSketch</title>
        <meta name="description" content="Free AI system design tool. Describe your architecture in plain English and get instant diagrams. Create AWS, microservices, and cloud architecture diagrams in seconds. Perfect for system design interview prep." />
        <meta name="keywords" content="system design tool, AI diagram generator, architecture diagram generator, system design interview prep, ai architecture generator, system design diagram, aws architecture diagram generator, cloud architecture tool, microservices design, system design online tool" />
        <link rel="canonical" href="https://infrasketch.net/" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://infrasketch.net/" />
        <meta property="og:title" content="InfraSketch - AI System Design Tool" />
        <meta property="og:description" content="Transform ideas into professional system architecture diagrams with AI. Free to use." />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />
        <meta property="og:site_name" content="InfraSketch" />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch - AI System Design Tool" />
        <meta name="twitter:description" content="Transform ideas into professional system architecture diagrams with AI." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        {/* Structured Data */}
        <script type="application/ld+json">
          {JSON.stringify(structuredData)}
        </script>
      </Helmet>

      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Describe a System.<br />
            Watch It Come to Life.
          </h1>
          <p className="hero-subtitle">
            InfraSketch's AI agent turns your ideas into architecture diagrams. Chat to iterate, ask questions, and refine. Then export a design doc and start building.
          </p>
          <p className="hero-cta">No drag-and-drop. No blank canvas paralysis. Just describe what you need.</p>
          <p className="hero-secondary">Perfect for prototyping, learning, or prepping for system design interviews.</p>
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
            {loading ? 'Sketching...' : 'Sketch My System'}
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
                <span className="example-icon"><example.icon size={20} /></span>
                <span className="example-title">{example.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* The Problem Section */}
      <div
        ref={problemAnimation.ref}
        className={`problem-section scroll-animate ${problemAnimation.isVisible ? 'visible' : ''}`}
      >
        <h2 className="problem-heading">The Problem</h2>
        <p className="problem-lead">
          Designing systems is hard. Turning ideas into clear architecture takes too long.
        </p>
        <ul className="problem-list">
          <li>Diagramming tools are slow and tedious</li>
          <li>AI chatbots explain but cannot build</li>
          <li>Blank canvases lead to decision paralysis</li>
          <li>Docs get outdated before you finish writing them</li>
        </ul>
        <p className="problem-conclusion">
          You need a tool that builds with you, not just talks at you.
        </p>
      </div>

      {/* Features Section */}
      <div
        ref={featuresAnimation.ref}
        className={`features-section scroll-animate ${featuresAnimation.isVisible ? 'visible' : ''}`}
      >
        <h2 className="features-heading">The Solution</h2>
        <div className="features-grid">
          {FEATURES.map((feature, index) => (
            <div
              key={index}
              ref={featureCards[index].ref}
              className={`feature-card scroll-animate ${featureCards[index].isVisible ? 'visible' : ''}`}
              style={featureCards[index].style}
            >
              <div className="feature-icon"><feature.icon size={32} /></div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Screenshots Showcase - Carousel */}
      <div
        ref={showcaseAnimation.ref}
        className={`showcase-section scroll-animate ${showcaseAnimation.isVisible ? 'visible' : ''}`}
      >
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
      <div
        ref={howItWorksAnimation.ref}
        className={`how-it-works-section scroll-animate ${howItWorksAnimation.isVisible ? 'visible' : ''}`}
      >
        <h2 className="how-it-works-heading">How It Works</h2>
        <div className="steps-grid">
          <div
            ref={stepCards[0].ref}
            className={`step-card scroll-animate ${stepCards[0].isVisible ? 'visible' : ''}`}
            style={stepCards[0].style}
          >
            <div className="step-number">1</div>
            <h3 className="step-title">Describe Your System</h3>
            <p className="step-description">
              Tell the AI what you want to build in plain English. No templates, no drag-and-drop, just describe it.
            </p>
          </div>
          <div
            ref={stepCards[1].ref}
            className={`step-card scroll-animate ${stepCards[1].isVisible ? 'visible' : ''}`}
            style={stepCards[1].style}
          >
            <div className="step-number">2</div>
            <h3 className="step-title">Generate & Iterate</h3>
            <p className="step-description">
              Watch your architecture appear in seconds. Ask questions, request changes, and refine your design through conversation.
            </p>
          </div>
          <div
            ref={stepCards[2].ref}
            className={`step-card scroll-animate ${stepCards[2].isVisible ? 'visible' : ''}`}
            style={stepCards[2].style}
          >
            <div className="step-number">3</div>
            <h3 className="step-title">Export & Build</h3>
            <p className="step-description">
              Generate a comprehensive design doc with architecture diagrams, component details, and implementation notes. Then start building.
            </p>
          </div>
        </div>
      </div>

      {/* Featured On Section */}
      <div
        ref={featuredOnAnimation.ref}
        className={`featured-on-section scroll-animate ${featuredOnAnimation.isVisible ? 'visible' : ''}`}
      >
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

          {/* NextGen Tools */}
          <a
            href="https://www.nxgntools.com/tools/infrasketch?utm_source=infrasketch"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://www.nxgntools.com/api/embed/infrasketch?type=FIND_US_ON&hideUpvotes=true"
              alt="NextGen Tools Badge - The #1 AI Tools Directory & Launch Platform"
              className="featured-badge-img"
              style={{ height: '48px', width: 'auto' }}
            />
          </a>

          {/* LaunchIgniter */}
          <a
            href="https://launchigniter.com/product/infrasketch?ref=badge-infrasketch"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://launchigniter.com/api/badge/infrasketch?theme=dark"
              alt="Featured on LaunchIgniter"
              className="featured-badge-img"
              width="212"
              height="55"
            />
          </a>

        </div>
      </div>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">AI-powered system design</p>
          </div>
          <div className="footer-links">
            <a href="/about">About</a>
            <a href="/blog">Blog</a>
            <a href="/pricing">Pricing</a>
            <a href="/careers">Careers</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
            <a href="/contact">Contact</a>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 InfraSketch. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
