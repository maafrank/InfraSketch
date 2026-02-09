import { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useScrollAnimation, useStaggeredAnimation } from '../hooks/useScrollAnimation';
import { Twitter, ShoppingCart, Link, Tv, Pencil, MessageSquare, Brain, FileText, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link as RouterLink } from 'react-router-dom';
import Footer from './shared/Footer';

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
    description: "Skip the drag-and-drop. Describe what you're building and get a complete architecture diagram, with all the components and connections, in seconds."
  },
  {
    icon: MessageSquare,
    title: "Chat to Iterate",
    description: "Say 'add a cache layer' or 'what if we need 10x scale?' and the diagram updates live. Iterate as fast as you can think."
  },
  {
    icon: Brain,
    title: "Understand Every Component",
    description: "Click any node to ask why it's there, what the tradeoffs are, or what alternatives exist. Learn while you design."
  },
  {
    icon: FileText,
    title: "Export & Build",
    description: "Generate a design doc with component details, data flows, and implementation notes. Share it with your team or use it to start building."
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
  const [lightboxOpen, setLightboxOpen] = useState(false);

  // Scroll animations for sections
  const problemAnimation = useScrollAnimation();
  const featuresAnimation = useScrollAnimation();
  const showcaseAnimation = useScrollAnimation();
  const howItWorksAnimation = useScrollAnimation();
  const featuredOnAnimation = useScrollAnimation();
  const pricingAnimation = useScrollAnimation();

  // Staggered animations for cards
  const featureCards = useStaggeredAnimation(FEATURES.length, { staggerDelay: 100 });
  const stepCards = useStaggeredAnimation(3, { staggerDelay: 150 });

  // Auto-rotate screenshots every 4 seconds (pauses when lightbox is open)
  useEffect(() => {
    if (lightboxOpen) return;

    const interval = setInterval(() => {
      setCurrentScreenshot((prev) => (prev + 1) % SCREENSHOTS.length);
    }, 4000);

    return () => clearInterval(interval);
  }, [lightboxOpen]);

  // Handle keyboard navigation in lightbox
  useEffect(() => {
    if (!lightboxOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setLightboxOpen(false);
      } else if (e.key === 'ArrowLeft') {
        setCurrentScreenshot((prev) =>
          prev === 0 ? SCREENSHOTS.length - 1 : prev - 1
        );
      } else if (e.key === 'ArrowRight') {
        setCurrentScreenshot((prev) =>
          (prev + 1) % SCREENSHOTS.length
        );
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [lightboxOpen]);

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
            Describe your system in plain English. Get an architecture diagram in seconds. Refine it through conversation, then export a design doc your team can actually use.
          </p>
          <p className="hero-cta">No drag-and-drop. No blank canvas. Just describe what you need.</p>
          <p className="hero-secondary">Used by engineers for prototyping, by students for learning, and by candidates prepping for system design interviews.</p>
        </div>

        {/* Main Input Form - Front and Center */}
        <form onSubmit={handleSubmit} className="landing-input-form">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your system architecture or paste a GitHub URL to analyze an existing repo..."
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
          You have a system in your head, but getting it on paper takes longer than it should.
        </p>
        <ul className="problem-list">
          <li>Drag-and-drop tools make you think about boxes and arrows, not architecture</li>
          <li>AI chatbots explain concepts but leave you with nothing to share</li>
          <li>Starting from a blank canvas means making every decision at once</li>
          <li>Design docs take hours to write and are outdated by the time you finish</li>
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
        <h2 className="features-heading">What You Get</h2>
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
                    onClick={() => setLightboxOpen(true)}
                    style={{ cursor: 'pointer' }}
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
              Type a description of your system, like "Design a URL shortener with analytics and high availability." That's it.
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
              Your diagram appears in seconds with all components connected. Then chat to tweak it, one message at a time.
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
              Export a full design doc, ready to share with your team, attach to a ticket, or use as a blueprint. From idea to document in minutes.
            </p>
          </div>
        </div>
      </div>

      {/* Transparent Pricing Section */}
      <div
        ref={pricingAnimation.ref}
        className={`pricing-section scroll-animate ${pricingAnimation.isVisible ? 'visible' : ''}`}
      >
        <h2 className="pricing-heading">Transparent Pricing</h2>
        <p className="pricing-subtext">25 free credits every month. Here's what they cost.</p>
        <div className="pricing-grid">
          <div className="pricing-card" data-tooltip="Describe any system and Claude designs a complete architecture with 4-8 connected components, auto-organized into semantic groups">
            <span className="pricing-action">Diagram Generation</span>
            <span className="pricing-amount">5-15 credits</span>
            <span className="pricing-note">5 (Haiku) / 15 (Sonnet)</span>
          </div>
          <div className="pricing-card" data-tooltip="Refine your diagram through conversation. Claude can add, remove, or update components, create connections, and organize nodes into groups">
            <span className="pricing-action">Chat Message</span>
            <span className="pricing-amount">1-3 credits</span>
            <span className="pricing-note">1 (Haiku) / 3 (Sonnet)</span>
          </div>
          <div className="pricing-card" data-tooltip="Claude writes a full technical document covering architecture overview, component details, data flow, scalability, security, and trade-offs">
            <span className="pricing-action">Design Doc</span>
            <span className="pricing-amount">10 credits</span>
            <span className="pricing-note">Per document</span>
          </div>
          <div className="pricing-card" data-tooltip="Download a professionally formatted PDF with your diagram embedded, or export as Markdown and PNG for docs and presentations">
            <span className="pricing-action">Export</span>
            <span className="pricing-amount">2 credits</span>
            <span className="pricing-note">PDF or Markdown</span>
          </div>
        </div>
        <p className="pricing-footer">
          That's 5 diagrams, 25 chat messages, or a mix. Upgrade to Pro for 500 credits/month.
        </p>
        <RouterLink to="/pricing" className="pricing-cta-link">See full pricing</RouterLink>
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

          {/* TechTrendin */}
          <a
            href="https://www.techtrendin.com/products/infrasketch"
            target="_blank"
            rel="noopener noreferrer"
            className="featured-badge-link"
          >
            <img
              src="https://www.techtrendin.com/badges/featured-dark.png"
              alt="Featured on TechTrendin"
              className="featured-badge-img"
              style={{ height: '52px', width: 'auto' }}
            />
          </a>

        </div>
      </div>

      {/* Lightbox Modal */}
      {lightboxOpen && (
        <div
          className="lightbox-overlay"
          onClick={() => setLightboxOpen(false)}
        >
          <button
            className="lightbox-close"
            onClick={() => setLightboxOpen(false)}
            aria-label="Close lightbox"
          >
            <X size={32} />
          </button>

          <button
            className="lightbox-nav lightbox-prev"
            onClick={(e) => {
              e.stopPropagation();
              setCurrentScreenshot((prev) =>
                prev === 0 ? SCREENSHOTS.length - 1 : prev - 1
              );
            }}
            aria-label="Previous image"
          >
            <ChevronLeft size={48} />
          </button>

          <div
            className="lightbox-content"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={SCREENSHOTS[currentScreenshot].src}
              alt={SCREENSHOTS[currentScreenshot].alt}
              className="lightbox-image"
            />
            <p className="lightbox-caption">
              {SCREENSHOTS[currentScreenshot].caption}
            </p>
            <p className="lightbox-counter">
              {currentScreenshot + 1} / {SCREENSHOTS.length}
            </p>
          </div>

          <button
            className="lightbox-nav lightbox-next"
            onClick={(e) => {
              e.stopPropagation();
              setCurrentScreenshot((prev) =>
                (prev + 1) % SCREENSHOTS.length
              );
            }}
            aria-label="Next image"
          >
            <ChevronRight size={48} />
          </button>
        </div>
      )}

      <Footer />
    </div>
  );
}
