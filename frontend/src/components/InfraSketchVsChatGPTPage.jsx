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
  { feature: "Visual Diagram Output", infrasketch: true, chatgpt: false },
  { feature: "Natural Language Input", infrasketch: true, chatgpt: true },
  { feature: "Auto Design Document Generation", infrasketch: true, chatgpt: false },
  { feature: "Chat-Based Refinement", infrasketch: true, chatgpt: true },
  { feature: "Architecture-Specific Understanding", infrasketch: true, chatgpt: false },
  { feature: "Persistent Diagram Storage", infrasketch: true, chatgpt: false },
  { feature: "Export to PNG/PDF", infrasketch: true, chatgpt: false },
  { feature: "Works Without Other Tools", infrasketch: true, chatgpt: false },
  { feature: "Multiple Diagram Types", infrasketch: false, chatgpt: true },
  { feature: "General-Purpose AI Assistant", infrasketch: false, chatgpt: true },
  { feature: "Free Tier", infrasketch: true, chatgpt: true }
];

const FAQS = [
  {
    question: "Can ChatGPT create architecture diagrams?",
    answer: "ChatGPT can generate Mermaid diagram code, which you then need to render using a separate tool like the Mermaid Live Editor or a Mermaid plugin. The output is text-based code, not a visual diagram. InfraSketch generates interactive, visual architecture diagrams directly in the browser."
  },
  {
    question: "How does InfraSketch compare to ChatGPT for diagrams?",
    answer: "InfraSketch is purpose-built for system architecture diagrams. It generates visual, interactive diagrams with auto-layout, component grouping, and design documents. ChatGPT generates Mermaid code that requires a separate rendering step and does not include design documentation."
  },
  {
    question: "Do I need to know Mermaid syntax to use InfraSketch?",
    answer: "No. InfraSketch uses natural language input and generates visual diagrams directly. There is no code syntax to learn. With ChatGPT, you often need to understand Mermaid syntax to fix or customize the generated diagram code."
  },
  {
    question: "Which is better for system design interviews?",
    answer: "InfraSketch is optimized for system design practice. It generates both architecture diagrams and comprehensive design documents from a single prompt, then lets you refine through conversation. ChatGPT can help with system design concepts, but the diagram workflow requires extra steps to visualize."
  },
  {
    question: "Can I use both ChatGPT and InfraSketch together?",
    answer: "Yes. Many engineers use ChatGPT for brainstorming and research, then use InfraSketch to create the actual architecture diagrams and design documents. The tools complement each other well since they serve different purposes."
  }
];

export default function InfraSketchVsChatGPTPage() {
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
        "name": "InfraSketch vs ChatGPT + Mermaid - AI Diagram Tool Comparison",
        "description": "Compare InfraSketch's visual AI diagram generation with ChatGPT's Mermaid code output. See which approach works better for system architecture diagrams.",
        "url": "https://infrasketch.net/compare/chatgpt"
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
            "name": "InfraSketch vs ChatGPT",
            "item": "https://infrasketch.net/compare/chatgpt"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs ChatGPT + Mermaid | AI Diagram Tool Comparison 2026</title>
        <meta name="description" content="Compare InfraSketch's visual AI diagram generation with ChatGPT's Mermaid code output. See which approach works better for system architecture diagrams." />
        <meta name="keywords" content="infrasketch vs chatgpt, chatgpt mermaid diagrams, ai diagram generator, chatgpt architecture diagram" />
        <link rel="canonical" href="https://infrasketch.net/compare/chatgpt" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs ChatGPT + Mermaid | AI Diagram Tool Comparison" />
        <meta property="og:description" content="Compare InfraSketch's visual AI diagram generation with ChatGPT's Mermaid code output. See which approach works better for system architecture diagrams." />
        <meta property="og:url" content="https://infrasketch.net/compare/chatgpt" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs ChatGPT + Mermaid | AI Diagram Tool Comparison" />
        <meta name="twitter:description" content="Compare InfraSketch's visual AI diagram generation with ChatGPT's Mermaid code output." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs ChatGPT + Mermaid
        </h1>
        <p className="tool-hero-subtitle">
          ChatGPT generates Mermaid code you render separately. InfraSketch generates visual, interactive
          architecture diagrams directly, with design documents included.
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
          ChatGPT generates Mermaid code that you render separately. InfraSketch generates visual,
          interactive architecture diagrams directly, with design documents included. No copy-paste,
          no external renderer needed.
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
                <th>ChatGPT + Mermaid</th>
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
                    {row.chatgpt ? (
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
                <td>Free tier, Plus from $20/mo</td>
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
            <h3>ChatGPT + Mermaid</h3>
            <p className="tool-tagline">General-Purpose AI with Code-Based Diagrams</p>
            <ul className="pros-list">
              <li>Powerful general-purpose AI assistant</li>
              <li>Generates multiple diagram types via Mermaid syntax</li>
              <li>Free with ChatGPT subscription</li>
              <li>Works with GitHub and Notion embeds</li>
              <li>Conversational refinement of diagram code</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Quick diagrams in documentation when you already use ChatGPT and are comfortable with Mermaid syntax
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
              <li>You need both diagrams AND design documentation</li>
              <li>You want visual, interactive architecture diagrams</li>
              <li>You're preparing for system design interviews</li>
              <li>You want to iterate on architecture through conversation</li>
              <li>You prefer a purpose-built tool over copy-pasting code</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Choose ChatGPT + Mermaid when...</h3>
            <ul>
              <li>You need quick diagrams inside existing documentation</li>
              <li>You already use ChatGPT for other development tasks</li>
              <li>You are comfortable reading and editing Mermaid syntax</li>
              <li>You need sequence diagrams, ER diagrams, or flowcharts</li>
              <li>You want diagrams embedded in GitHub READMEs or Notion</li>
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
            <p>Compare AI diagram generation with whiteboard-focused collaboration tools.</p>
          </Link>
          <Link to="/compare/mermaid" className="learn-more-card">
            <span className="learn-more-icon">📐</span>
            <h3>InfraSketch vs Mermaid</h3>
            <p>Compare visual AI diagrams with code-based Mermaid diagram syntax.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">⚖️</span>
            <h3>Full Tool Comparison</h3>
            <p>Compare InfraSketch with Lucidchart, Eraser, Draw.io, and Miro.</p>
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
