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
    src: "/full-app-with-design-doc.png",
    alt: "Full application with session history, design doc, and diagram",
    caption: "Manage multiple designs with session history"
  }
];

const COMPARISON_DATA = [
  { feature: "Natural Language Input", infrasketch: true, mermaid: false },
  { feature: "AI-Powered Generation", infrasketch: true, mermaid: false },
  { feature: "Chat-Based Refinement", infrasketch: true, mermaid: false },
  { feature: "Auto Design Documents", infrasketch: true, mermaid: false },
  { feature: "No Syntax to Learn", infrasketch: true, mermaid: false },
  { feature: "Diagram-as-Code", infrasketch: false, mermaid: true },
  { feature: "Git-Friendly (Text-Based)", infrasketch: false, mermaid: true },
  { feature: "Markdown Integration", infrasketch: false, mermaid: true },
  { feature: "Sequence Diagrams", infrasketch: false, mermaid: true },
  { feature: "Architecture Diagrams", infrasketch: true, mermaid: true },
  { feature: "Open Source", infrasketch: false, mermaid: true },
  { feature: "Free to Use", infrasketch: true, mermaid: true }
];

const FAQS = [
  {
    question: "What is Mermaid?",
    answer: "Mermaid is an open-source JavaScript library that generates diagrams from text-based syntax (diagram-as-code). You write diagram definitions in a markdown-like syntax, and Mermaid renders them as SVG images. It is widely integrated into GitHub, GitLab, Notion, and documentation tools."
  },
  {
    question: "What is D2?",
    answer: "D2 is a modern diagram-as-code tool (similar to Mermaid) that uses a declarative language to create diagrams. It focuses on software architecture diagrams with features like automatic layout, themes, and animations. D2 diagrams are text files that can be version-controlled."
  },
  {
    question: "How does InfraSketch compare to Mermaid and D2?",
    answer: "Mermaid and D2 require learning a specific syntax to define diagrams. InfraSketch uses natural language, so you describe your system in plain English and the AI generates the architecture. InfraSketch also generates design documents and lets you refine through conversation, which diagram-as-code tools do not support."
  },
  {
    question: "When should I use Mermaid over InfraSketch?",
    answer: "Use Mermaid when you need diagrams embedded in markdown documentation (README files, wikis), when you want version-controlled diagrams in Git, or when you need diagram types InfraSketch does not focus on (sequence diagrams, Gantt charts, state diagrams). Mermaid is also better for CI/CD pipeline diagrams that need to stay in sync with code."
  },
  {
    question: "Can I export InfraSketch diagrams to Mermaid?",
    answer: "InfraSketch currently exports to PNG, PDF, and Markdown formats. While there is no direct Mermaid syntax export, you can use the generated diagram as a reference to create a Mermaid version for your documentation, or use the exported PNG directly."
  }
];

export default function InfraSketchVsMermaidPage() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [currentScreenshot, setCurrentScreenshot] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  useEffect(() => {
    if (lightboxOpen) return;
    const interval = setInterval(() => {
      setCurrentScreenshot((prev) => (prev + 1) % SCREENSHOTS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [lightboxOpen]);

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
        "name": "InfraSketch vs Mermaid/D2 - Natural Language vs Diagram-as-Code",
        "description": "Compare InfraSketch with Mermaid and D2. InfraSketch uses natural language for AI diagram generation, Mermaid and D2 use code-based syntax.",
        "url": "https://infrasketch.net/compare/mermaid"
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
            "name": "InfraSketch vs Mermaid",
            "item": "https://infrasketch.net/compare/mermaid"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs Mermaid & D2 | Natural Language vs Diagram-as-Code</title>
        <meta name="description" content="Compare InfraSketch with Mermaid and D2 for architecture diagrams. InfraSketch uses natural language and AI, Mermaid and D2 use code-based syntax. See which approach fits your workflow." />
        <meta name="keywords" content="mermaid alternative, d2 alternative, diagram as code vs ai, mermaid vs infrasketch, architecture diagram tool comparison, natural language diagram" />
        <link rel="canonical" href="https://infrasketch.net/compare/mermaid" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs Mermaid & D2 | Natural Language vs Diagram-as-Code" />
        <meta property="og:description" content="Compare natural language diagram generation with diagram-as-code tools." />
        <meta property="og:url" content="https://infrasketch.net/compare/mermaid" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs Mermaid & D2" />
        <meta name="twitter:description" content="Compare natural language diagrams with diagram-as-code tools." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs Mermaid & D2
        </h1>
        <p className="tool-hero-subtitle">
          Mermaid and D2 generate diagrams from code syntax.
          InfraSketch generates diagrams from plain English.
          No syntax to learn, no code to write.
        </p>

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

      {/* Screenshots Showcase */}
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
          Mermaid and D2 require you to <strong>learn a syntax</strong> and manually write diagram definitions.
          InfraSketch lets you <strong>describe your system in plain English</strong> and generates the architecture
          automatically. InfraSketch also generates comprehensive design documents and lets you refine
          your architecture through natural conversation.
        </p>
      </div>

      {/* Code Comparison */}
      <div className="tool-section">
        <h2>Input Comparison</h2>
        <div className="side-by-side-grid">
          <div className="side-by-side-card highlight">
            <h3>InfraSketch (Natural Language)</h3>
            <p className="tool-tagline" style={{ fontFamily: 'monospace', fontSize: '14px', background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', textAlign: 'left' }}>
              "Design a web application with a load balancer, two API servers, a Redis cache, and a PostgreSQL database"
            </p>
          </div>
          <div className="side-by-side-card">
            <h3>Mermaid (Code Syntax)</h3>
            <p className="tool-tagline" style={{ fontFamily: 'monospace', fontSize: '12px', background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', textAlign: 'left', whiteSpace: 'pre-wrap' }}>
{`graph TD
  LB[Load Balancer]
  API1[API Server 1]
  API2[API Server 2]
  Cache[Redis Cache]
  DB[(PostgreSQL)]
  LB --> API1
  LB --> API2
  API1 --> Cache
  API2 --> Cache
  API1 --> DB
  API2 --> DB`}
            </p>
          </div>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="tool-section tool-section-alt">
        <h2>Feature Comparison</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th className="highlight">InfraSketch</th>
                <th>Mermaid / D2</th>
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
                    {row.mermaid ? (
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
                <td>Free and open-source</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* When to Use */}
      <div className="tool-section">
        <h2>When to Use Each</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>Use InfraSketch when...</h3>
            <ul>
              <li>You want to generate diagrams without learning syntax</li>
              <li>You need to quickly explore architecture ideas</li>
              <li>You want auto-generated design documentation</li>
              <li>You are designing complex system architectures</li>
              <li>You want AI assistance in architecture decisions</li>
              <li>You are preparing for system design interviews</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Use Mermaid/D2 when...</h3>
            <ul>
              <li>You need diagrams embedded in markdown docs</li>
              <li>You want version-controlled diagrams in Git</li>
              <li>You need sequence diagrams, Gantt charts, or ER diagrams</li>
              <li>You need diagrams in CI/CD documentation</li>
              <li>You prefer code-based tools in your workflow</li>
              <li>You need diagrams in GitHub READMEs</li>
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
            <span className="learn-more-icon">🎨</span>
            <h3>InfraSketch vs Eraser</h3>
            <p>Compare two AI-powered diagramming tools with different focuses.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">📊</span>
            <h3>Full Tool Comparison</h3>
            <p>Compare InfraSketch with Lucidchart, Eraser, Draw.io, and Miro.</p>
          </Link>
          <Link to="/blog/top-7-architecture-diagram-tools" className="learn-more-card">
            <span className="learn-more-icon">🏆</span>
            <h3>Top 7 Architecture Tools</h3>
            <p>Detailed comparison of the best architecture diagram tools available.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Skip the Syntax. Describe Your System.</h2>
        <p>Generate architecture diagrams from plain English. No syntax to learn, no code to write.</p>
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
