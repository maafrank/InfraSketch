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
    caption: "Choose between Speed and Power models"
  }
];

const COMPARISON_DATA = [
  { feature: "Full AI Diagram Generation", infrasketch: true, whimsical: false },
  { feature: "Natural Language Input", infrasketch: true, whimsical: true },
  { feature: "Auto Design Document Generation", infrasketch: true, whimsical: false },
  { feature: "Chat-Based Refinement", infrasketch: true, whimsical: false },
  { feature: "Flowchart Creation", infrasketch: false, whimsical: true },
  { feature: "Mind Maps", infrasketch: false, whimsical: true },
  { feature: "Wireframing", infrasketch: false, whimsical: true },
  { feature: "Real-Time Collaboration", infrasketch: false, whimsical: true },
  { feature: "Export to PNG", infrasketch: true, whimsical: true },
  { feature: "Export to PDF", infrasketch: true, whimsical: true },
  { feature: "Free Tier", infrasketch: true, whimsical: true }
];

const FAQS = [
  {
    question: "What is Whimsical?",
    answer: "Whimsical is a visual workspace for creating flowcharts, mind maps, wireframes, and documents. It offers a polished, intuitive interface for teams to collaborate on visual artifacts like user flows and product planning."
  },
  {
    question: "How does InfraSketch compare to Whimsical?",
    answer: "InfraSketch is purpose-built for software architecture diagrams with full AI generation and automatic design documents. Whimsical is a broader visual tool focused on flowcharts, mind maps, and wireframes. They serve different use cases with little overlap."
  },
  {
    question: "Can Whimsical generate architecture diagrams with AI?",
    answer: "Whimsical has some AI features for generating flowcharts and mind maps, but it does not generate software architecture diagrams from natural language descriptions. InfraSketch is specifically designed for this, turning a text prompt into a full system design."
  },
  {
    question: "Which tool is better for system design interviews?",
    answer: "InfraSketch is built for system design workflows. You describe a system, get an instant architecture diagram, refine it through chat, and generate a design document. Whimsical is better suited for product design tasks like user flows and wireframes."
  },
  {
    question: "Can I use both tools together?",
    answer: "Yes. Many teams use InfraSketch for backend architecture and system design, then use Whimsical for product-facing artifacts like user journey maps, wireframes, and flowcharts. The two tools complement each other well."
  }
];

export default function InfraSketchVsWhimsicalPage() {
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
        "name": "InfraSketch vs Whimsical - Architecture Diagrams vs Flowcharts",
        "description": "Compare InfraSketch for system architecture diagrams with Whimsical for flowcharts and mind maps. Find the right AI diagramming tool for your needs.",
        "url": "https://infrasketch.net/compare/whimsical"
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
            "name": "InfraSketch vs Whimsical",
            "item": "https://infrasketch.net/compare/whimsical"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs Whimsical | Architecture Diagrams vs Flowcharts 2026</title>
        <meta name="description" content="Compare InfraSketch for system architecture diagrams with Whimsical for flowcharts and mind maps. Find the right AI diagramming tool for your needs." />
        <meta name="keywords" content="infrasketch vs whimsical, whimsical alternative, ai diagram tool comparison, whimsical ai vs infrasketch" />
        <link rel="canonical" href="https://infrasketch.net/compare/whimsical" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs Whimsical | Architecture Diagrams vs Flowcharts" />
        <meta property="og:description" content="Compare InfraSketch for system architecture diagrams with Whimsical for flowcharts and mind maps." />
        <meta property="og:url" content="https://infrasketch.net/compare/whimsical" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs Whimsical | Architecture Diagrams vs Flowcharts" />
        <meta name="twitter:description" content="Compare InfraSketch for system architecture diagrams with Whimsical for flowcharts and mind maps." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs Whimsical
        </h1>
        <p className="tool-hero-subtitle">
          Whimsical is a visual workspace for flowcharts, mind maps, and wireframes.
          InfraSketch is purpose-built for AI-generated architecture diagrams with auto design documents.
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
          Whimsical excels at flowcharts, mind maps, and wireframes. InfraSketch is purpose-built for
          software architecture diagrams with AI generation and auto design documents.
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
                <th>Whimsical</th>
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
                    {row.whimsical ? (
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
                <td>Free tier, paid from $10/mo</td>
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
              <li><strong>Unique:</strong> Auto-generates comprehensive design documents</li>
              <li><strong>Unique:</strong> Chat-based refinement of diagrams</li>
              <li>Natural language to architecture diagrams</li>
              <li>Optimized for system design practice</li>
              <li>Export to PNG, PDF, and Markdown</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Engineers who want diagrams AND documentation from a single description
            </div>
            <Link to="/" className="tool-try-button">Try InfraSketch Free</Link>
          </div>
          <div className="side-by-side-card">
            <h3>Whimsical</h3>
            <p className="tool-tagline">Visual Workspace for Flowcharts and Mind Maps</p>
            <ul className="pros-list">
              <li>Beautiful, polished visual output</li>
              <li>Excellent flowchart creation</li>
              <li>Mind mapping tools</li>
              <li>Wireframing capabilities</li>
              <li>Team collaboration built in</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Product teams needing flowcharts, user journeys, and wireframes in a polished workspace
            </div>
          </div>
        </div>
      </div>

      {/* When to Use */}
      <div className="tool-section">
        <h2>When to Use Each Tool</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>Choose InfraSketch when...</h3>
            <ul>
              <li>You need AI-generated software architecture diagrams</li>
              <li>You want automatic design documentation alongside diagrams</li>
              <li>You're preparing for system design interviews</li>
              <li>You prefer describing systems in natural language over manual drawing</li>
              <li>You want to iterate on architecture through conversation</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Choose Whimsical when...</h3>
            <ul>
              <li>You need polished flowcharts or user journey maps</li>
              <li>Mind mapping is central to your planning process</li>
              <li>You need wireframing for product design</li>
              <li>Real-time team collaboration is a priority</li>
              <li>You want a general-purpose visual workspace for multiple diagram types</li>
            </ul>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="tool-section tool-section-alt">
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
      <div className="tool-section">
        <h2>Related Comparisons</h2>
        <div className="learn-more-grid">
          <Link to="/compare/eraser" className="learn-more-card">
            <span className="learn-more-icon">📊</span>
            <h3>InfraSketch vs Eraser</h3>
            <p>Compare AI diagram generation with whiteboard-focused diagramming.</p>
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
        <h2>Try the Only AI Tool with Auto Design Documents</h2>
        <p>Create diagrams and comprehensive documentation in minutes. No signup required.</p>
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
