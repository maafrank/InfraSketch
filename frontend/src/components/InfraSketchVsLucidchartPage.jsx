import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Twitter, ShoppingCart, Link as LinkIcon, Tv, X, ChevronLeft, ChevronRight } from 'lucide-react';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

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
    icon: LinkIcon
  },
  {
    title: "Video Streaming",
    prompt: "Design a video streaming platform like YouTube with upload, transcoding, and CDN",
    icon: Tv
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

const COMPARISON_DATA = [
  { feature: "AI Diagram Generation", infrasketch: true, lucidchart: false },
  { feature: "Natural Language Input", infrasketch: true, lucidchart: false },
  { feature: "Auto Design Document Generation", infrasketch: true, lucidchart: false },
  { feature: "Chat-Based Refinement", infrasketch: true, lucidchart: false },
  { feature: "Drag-and-Drop Editor", infrasketch: false, lucidchart: true },
  { feature: "Real-Time Collaboration", infrasketch: false, lucidchart: true },
  { feature: "Extensive Shape Libraries", infrasketch: false, lucidchart: true },
  { feature: "Cloud Provider Icons", infrasketch: true, lucidchart: true },
  { feature: "Export to PNG", infrasketch: true, lucidchart: true },
  { feature: "Export to PDF", infrasketch: true, lucidchart: true },
  { feature: "Free Tier", infrasketch: true, lucidchart: true }
];

const FAQS = [
  {
    question: "What is Lucidchart?",
    answer: "Lucidchart is a traditional diagramming tool with a drag-and-drop interface. It offers extensive shape libraries, templates, and real-time collaboration features for creating flowcharts, org charts, and architecture diagrams."
  },
  {
    question: "How does InfraSketch compare to Lucidchart?",
    answer: "Lucidchart is a manual diagramming tool where you drag shapes onto a canvas. InfraSketch uses AI to generate diagrams from natural language descriptions. InfraSketch also auto-generates design documents, which Lucidchart cannot do."
  },
  {
    question: "Is InfraSketch a Lucidchart alternative?",
    answer: "Yes, for system architecture diagrams. InfraSketch replaces manual diagramming with AI generation. Instead of dragging components, you describe your system and get a complete diagram. You can then refine it through chat."
  },
  {
    question: "Which is faster for creating architecture diagrams?",
    answer: "InfraSketch is significantly faster. A diagram that takes 30+ minutes in Lucidchart can be generated in seconds with InfraSketch. The AI understands system design concepts and creates appropriate components and connections automatically."
  },
  {
    question: "Does Lucidchart have AI features?",
    answer: "Lucidchart has added some AI features for auto-layout and suggestions, but it does not generate diagrams from natural language like InfraSketch does. You still need to manually drag and connect shapes in Lucidchart."
  },
  {
    question: "When should I use Lucidchart instead of InfraSketch?",
    answer: "Use Lucidchart when you need pixel-perfect control over diagram layout, are creating non-architecture diagrams (flowcharts, org charts), or need real-time collaboration. Use InfraSketch when you want to generate diagrams quickly from descriptions."
  }
];

export default function InfraSketchVsLucidchartPage() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [currentScreenshot, setCurrentScreenshot] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

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
        setCurrentScreenshot((prev) => prev === 0 ? SCREENSHOTS.length - 1 : prev - 1);
      } else if (e.key === 'ArrowRight') {
        setCurrentScreenshot((prev) => (prev + 1) % SCREENSHOTS.length);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [lightboxOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt.trim()) {
      navigate('/', { state: { initialPrompt: prompt } });
    }
  };

  const handleExampleClick = (examplePrompt) => {
    setPrompt(examplePrompt);
  };

  const handleDotClick = (index) => {
    setCurrentScreenshot(index);
  };

  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "name": "InfraSketch vs Lucidchart - Diagramming Tool Comparison",
        "description": "Compare InfraSketch AI diagram generation with Lucidchart drag-and-drop diagramming. See which tool is best for system design.",
        "url": "https://infrasketch.net/compare/lucidchart"
      },
      {
        "@type": "FAQPage",
        "mainEntity": FAQS.map(faq => ({
          "@type": "Question",
          "name": faq.question,
          "acceptedAnswer": {
            "@type": "Answer",
            "text": faq.answer
          }
        }))
      },
      {
        "@type": "BreadcrumbList",
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": "https://infrasketch.net"
          },
          {
            "@type": "ListItem",
            "position": 2,
            "name": "Compare",
            "item": "https://infrasketch.net/compare"
          },
          {
            "@type": "ListItem",
            "position": 3,
            "name": "InfraSketch vs Lucidchart",
            "item": "https://infrasketch.net/compare/lucidchart"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs Lucidchart | AI vs Drag-and-Drop Diagrams 2026</title>
        <meta name="description" content="Compare InfraSketch AI diagram generation with Lucidchart drag-and-drop diagramming. InfraSketch generates diagrams from text in seconds. See the full comparison." />
        <meta name="keywords" content="infrasketch vs lucidchart, lucidchart alternative, ai diagram generator, lucidchart vs ai, architecture diagram tool comparison" />
        <link rel="canonical" href="https://infrasketch.net/compare/lucidchart" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs Lucidchart | AI vs Drag-and-Drop Diagrams" />
        <meta property="og:description" content="Compare InfraSketch AI diagram generation with Lucidchart drag-and-drop diagramming. See which approach works best for you." />
        <meta property="og:url" content="https://infrasketch.net/compare/lucidchart" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs Lucidchart | AI vs Drag-and-Drop Diagrams" />
        <meta name="twitter:description" content="Compare InfraSketch AI diagram generation with Lucidchart drag-and-drop diagramming." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs Lucidchart
        </h1>
        <p className="tool-hero-subtitle">
          AI-powered generation vs traditional drag-and-drop. InfraSketch creates diagrams from natural language.
          Lucidchart requires manual shape placement.
        </p>

        {/* Main Input Form */}
        <form onSubmit={handleSubmit} className="landing-input-form">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your system architecture..."
            rows={4}
            className="landing-textarea"
          />
          <button
            type="submit"
            disabled={!prompt.trim()}
            className="landing-generate-button"
          >
            Sketch My System
          </button>
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
              >
                <span className="example-icon"><example.icon size={20} /></span>
                <span className="example-title">{example.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Screenshots Showcase - Carousel */}
      <div className="showcase-section">
        <h2 className="showcase-heading">See It In Action</h2>
        <div className="showcase-carousel">
          <div className="carousel-container">
            <div
              className="carousel-track"
              style={{ transform: `translateX(-${currentScreenshot * 100}%)` }}
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

      {/* Key Difference */}
      <div className="tool-section tool-section-highlight">
        <h2>The Key Difference</h2>
        <p className="tool-highlight-text">
          Lucidchart is a manual tool: you drag shapes onto a canvas and connect them yourself.
          InfraSketch is <strong>AI-first</strong>: describe your system in plain English, get a complete diagram in seconds,
          then refine it through conversation. InfraSketch also generates design documents automatically.
        </p>
      </div>

      {/* Comparison Table */}
      <div className="tool-section">
        <h2>Feature Comparison</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th className="highlight">InfraSketch</th>
                <th>Lucidchart</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_DATA.map((row, index) => (
                <tr key={index}>
                  <td className="feature-name">{row.feature}</td>
                  <td className="highlight">
                    {row.infrasketch ? (
                      <span className="check">&#10003;</span>
                    ) : (
                      <span className="cross">&#10007;</span>
                    )}
                  </td>
                  <td>
                    {row.lucidchart ? (
                      <span className="check">&#10003;</span>
                    ) : (
                      <span className="cross">&#10007;</span>
                    )}
                  </td>
                </tr>
              ))}
              <tr>
                <td className="feature-name">Pricing</td>
                <td className="highlight">Free tier available</td>
                <td>Free tier, paid from $7.95/mo</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Side by Side */}
      <div className="tool-section tool-section-alt">
        <h2>Side-by-Side Comparison</h2>
        <div className="side-by-side-grid">
          <div className="side-by-side-card highlight">
            <h3>InfraSketch</h3>
            <p className="tool-tagline">AI System Design Tool with Auto Documentation</p>
            <ul className="pros-list">
              <li><strong>AI-powered:</strong> Generate diagrams from natural language</li>
              <li><strong>Unique:</strong> Auto-generates comprehensive design documents</li>
              <li><strong>Unique:</strong> Chat-based refinement of diagrams</li>
              <li>Seconds to create vs minutes with drag-and-drop</li>
              <li>Optimized for system architecture</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Engineers who want to generate architecture diagrams quickly without manual diagramming
            </div>
            <Link to="/" className="tool-try-button">Try InfraSketch Free</Link>
          </div>
          <div className="side-by-side-card">
            <h3>Lucidchart</h3>
            <p className="tool-tagline">Traditional Drag-and-Drop Diagramming</p>
            <ul className="pros-list">
              <li>Drag-and-drop interface with precise control</li>
              <li>Extensive shape and template libraries</li>
              <li>Real-time team collaboration</li>
              <li>Multiple diagram types (flowcharts, org charts)</li>
              <li>Enterprise integrations (Confluence, Jira)</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Teams needing general-purpose diagramming with pixel-perfect control
            </div>
          </div>
        </div>
      </div>

      {/* Speed Comparison */}
      <div className="tool-section">
        <h2>Speed Comparison</h2>
        <div className="speed-comparison">
          <div className="speed-item">
            <div className="speed-tool">InfraSketch</div>
            <div className="speed-time">~30 seconds</div>
            <div className="speed-bar fast"></div>
            <p>Type a description, AI generates the diagram</p>
          </div>
          <div className="speed-item">
            <div className="speed-tool">Lucidchart</div>
            <div className="speed-time">~30 minutes</div>
            <div className="speed-bar slow"></div>
            <p>Find shapes, drag onto canvas, connect, style</p>
          </div>
        </div>
      </div>

      {/* When to Use */}
      <div className="tool-section tool-section-alt">
        <h2>When to Use Each Tool</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>Choose InfraSketch when...</h3>
            <ul>
              <li>You want to create diagrams in seconds, not minutes</li>
              <li>You need auto-generated design documentation</li>
              <li>You're preparing for system design interviews</li>
              <li>You prefer describing systems over dragging shapes</li>
              <li>You want AI to suggest architecture patterns</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Choose Lucidchart when...</h3>
            <ul>
              <li>You need pixel-perfect control over layout</li>
              <li>You're creating flowcharts or org charts</li>
              <li>Real-time collaboration is essential</li>
              <li>You need extensive shape libraries</li>
              <li>You already use Lucidchart in your organization</li>
            </ul>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="tool-section">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-list">
          {FAQS.map((faq, index) => (
            <div key={index} className="faq-item">
              <h3>{faq.question}</h3>
              <p>{faq.answer}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Learn More */}
      <div className="tool-section tool-section-alt">
        <h2>Related Comparisons</h2>
        <div className="learn-more-grid">
          <Link to="/compare/eraser" className="learn-more-card">
            <span className="learn-more-icon">🎨</span>
            <h3>InfraSketch vs Eraser</h3>
            <p>Compare two AI-powered diagram tools with different approaches.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">⚖️</span>
            <h3>Full Tool Comparison</h3>
            <p>Compare InfraSketch with Lucidchart, Eraser, Draw.io, and Miro.</p>
          </Link>
          <Link to="/tools/design-doc-generator" className="learn-more-card">
            <span className="learn-more-icon">📄</span>
            <h3>Design Doc Generator</h3>
            <p>Learn about InfraSketch's unique auto-documentation feature.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Skip the Drag-and-Drop. Try AI-Powered Diagramming.</h2>
        <p>Generate architecture diagrams in seconds. No manual diagramming required.</p>
        <Link to="/" className="tool-cta-button">
          Try InfraSketch Free
        </Link>
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
