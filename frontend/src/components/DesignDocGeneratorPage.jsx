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
    src: "/doc-page/08-doc-app-with-sync.png",
    alt: "Full InfraSketch workspace with diagram, design doc, and auto-sync indicator",
    caption: "Diagram and design doc, side by side — auto-syncing as you edit"
  },
  {
    src: "/doc-page/01-doc-panel-full.png",
    alt: "Full design document panel with structured sections",
    caption: "A real, structured design document — generated in under 2 minutes"
  },
  {
    src: "/doc-page/03-doc-component-details.png",
    alt: "Component Details section with Purpose, Type, Rationale, and Scaling for each component",
    caption: "Component Details: purpose, type, rationale, scaling — for every node"
  },
  {
    src: "/doc-page/04-doc-data-flow.png",
    alt: "Data Flow section describing how data moves through the system",
    caption: "Data Flow: concrete paths with latency and hit-rate targets"
  },
  {
    src: "/doc-page/05-doc-trade-offs.png",
    alt: "Trade-offs and Alternatives section showing chosen vs considered options",
    caption: "Trade-offs: chosen vs. considered, with rationale"
  },
  {
    src: "/doc-page/02-doc-executive-summary.png",
    alt: "Executive Summary and System Overview sections",
    caption: "Executive Summary plus Purpose, Goals, and Target Scale"
  },
  {
    src: "/doc-page/09-doc-second-example.png",
    alt: "Video streaming platform diagram with its design doc",
    caption: "Same flow for any system: video streaming, e-commerce, anything"
  },
  {
    src: "/doc-page/06-doc-toolbar.png",
    alt: "Rich text editor toolbar with Bold, Italic, H1, H2, list, and number controls",
    caption: "Edit inline with a rich text editor — bold, headings, lists"
  },
  {
    src: "/auto-sync-hero.png",
    alt: "Sync indicator visible in the design doc panel after a diagram change",
    caption: "Change the diagram, the doc auto-updates the relevant sections"
  }
];

const FEATURES = [
  {
    icon: "📄",
    title: "Auto-Generated Design Documents",
    description: "One click turns your architecture diagram into a comprehensive design document. No manual writing, no blank-page paralysis."
  },
  {
    icon: "🔄",
    title: "Auto-Sync With Your Diagram",
    description: "Add a node, swap a database, change a connection — the relevant sections of the doc update themselves. No regeneration. No stale specs."
  },
  {
    icon: "🤖",
    title: "AI Agent–Ready",
    description: "Hand the doc to Claude Code, Cursor, or ChatGPT and let them implement it. Structured markdown with named components, explicit data flows, and clear trade-offs — exactly what agents need."
  },
  {
    icon: "💬",
    title: "Chat-Based Editing",
    description: "Refine both diagram and documentation through natural conversation. Ask the AI to expand a section, change a technology, or rethink a trade-off."
  },
  {
    icon: "📊",
    title: "12 Standard Sections",
    description: "Executive Summary, System Overview, Component Details, Data Flow, Infrastructure, Scalability, Security, Trade-offs, Implementation Phases — every section a real design doc needs."
  },
  {
    icon: "📤",
    title: "Export PDF & Markdown",
    description: "Export as a professional PDF for stakeholders or Markdown for your wiki. The diagram is embedded in the PDF. Perfect for PRDs, RFCs, and onboarding docs."
  }
];

// Sections to highlight in the new "What a generated doc actually looks like" gallery.
const DOC_EXCERPTS = [
  {
    src: "/doc-page/02-doc-executive-summary.png",
    title: "Executive Summary + System Overview",
    description: "A 1-2 paragraph summary of system purpose, plus Purpose & Goals and Target Scale bullets.",
  },
  {
    src: "/doc-page/03-doc-component-details.png",
    title: "Component Details",
    description: "Every component gets Purpose, Type, Rationale, and Scaling. No hand-waving.",
  },
  {
    src: "/doc-page/04-doc-data-flow.png",
    title: "Data Flow",
    description: "Concrete request paths with cache hit-rate targets and latency budgets.",
  },
  {
    src: "/doc-page/05-doc-trade-offs.png",
    title: "Trade-offs & Alternatives",
    description: "What was Chosen, what was Considered, and the Rationale for each decision.",
  },
];

const COMPARISON = [
  { feature: "AI Diagram Generation", infrasketch: true, eraser: true, lucidchart: false, miro: true },
  { feature: "Auto Design Document Generation", infrasketch: true, eraser: false, lucidchart: false, miro: false },
  { feature: "Auto-Sync Diagram & Doc", infrasketch: true, eraser: false, lucidchart: false, miro: false },
  { feature: "Chat-Based Refinement", infrasketch: true, eraser: false, lucidchart: false, miro: false },
  { feature: "PDF Export", infrasketch: true, eraser: true, lucidchart: true, miro: true },
  { feature: "Markdown Export", infrasketch: true, eraser: true, lucidchart: false, miro: false },
  { feature: "Free Tier", infrasketch: true, eraser: true, lucidchart: true, miro: true }
];

const DOCUMENT_SECTIONS = [
  { title: "Executive Summary", description: "High-level overview of the system purpose and architecture" },
  { title: "System Overview", description: "Detailed description of the system and its components" },
  { title: "Architecture Diagram", description: "Visual representation embedded in the document" },
  { title: "Component Details", description: "Deep dive into each component, its role, and technology choices" },
  { title: "Data Flow", description: "How data moves through the system" },
  { title: "Infrastructure", description: "Deployment, hosting, and infrastructure requirements" },
  { title: "Scalability", description: "How the system handles growth and load" },
  { title: "Security", description: "Authentication, authorization, and security considerations" },
  { title: "Trade-offs", description: "Design decisions and their implications" },
  { title: "Implementation Phases", description: "Suggested rollout plan and milestones" },
  { title: "Future Enhancements", description: "Potential improvements and extensions" },
  { title: "Appendix", description: "Additional technical details and references" }
];

const FAQS = [
  {
    question: "What is a design document generator?",
    answer: "A design document generator automatically creates technical documentation from your system architecture. InfraSketch generates comprehensive design docs from your diagrams, including component details, data flows, scalability considerations, and implementation plans."
  },
  {
    question: "How is this different from writing docs manually?",
    answer: "Manual documentation takes hours and goes stale the moment you change the architecture. InfraSketch generates the initial doc in under 2 minutes — and then auto-syncs it. Add a node or change a connection, and the relevant sections of the doc update themselves. No regeneration. No diff-checking docs against diagrams."
  },
  {
    question: "What sections are included in generated docs?",
    answer: "Generated documents include 12 standard sections: Executive Summary, System Overview, Architecture Diagram, Component Details, Data Flow, Infrastructure, Scalability, Security, Trade-offs, Implementation Phases, Future Enhancements, and Appendix."
  },
  {
    question: "Can I edit the generated document?",
    answer: "Yes. The document opens in a rich text editor where you can make any changes. You can also use chat to ask the AI to modify specific sections. Export when you are satisfied."
  },
  {
    question: "What export formats are available?",
    answer: "Export as PDF for sharing with stakeholders, or Markdown for wikis and version control. The PDF includes the architecture diagram embedded in the document."
  }
];

export default function DesignDocGeneratorPage() {
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
        "@type": "SoftwareApplication",
        "name": "InfraSketch Design Document Generator",
        "description": "AI-powered tool that generates comprehensive design documents from system architecture diagrams",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net/tools/design-doc-generator",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "USD"
        }
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
            "name": "Tools",
            "item": "https://infrasketch.net/tools"
          },
          {
            "@type": "ListItem",
            "position": 3,
            "name": "Design Doc Generator",
            "item": "https://infrasketch.net/tools/design-doc-generator"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page">
      <Helmet>
        <title>Design Document Generator | Auto-Generate Design Docs from Diagrams | InfraSketch</title>
        <meta name="description" content="Generate comprehensive design documents from architecture diagrams automatically. The only AI tool that creates both diagrams AND documentation. Export to PDF or Markdown." />
        <meta name="keywords" content="design document generator, design doc generator, auto generate design document, system design documentation, architecture documentation tool, technical documentation generator, ai design document" />
        <link rel="canonical" href="https://infrasketch.net/tools/design-doc-generator" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="Design Document Generator | Auto-Generate Design Docs from Diagrams" />
        <meta property="og:description" content="Generate comprehensive design documents from architecture diagrams automatically. The only AI tool that creates both diagrams AND documentation." />
        <meta property="og:url" content="https://infrasketch.net/tools/design-doc-generator" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Design Document Generator | Auto-Generate Design Docs from Diagrams" />
        <meta name="twitter:description" content="Generate comprehensive design documents from architecture diagrams automatically. The only AI tool that creates both diagrams AND documentation." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          Design Document Generator
        </h1>
        <p className="tool-hero-subtitle">
          Generate a real, structured design doc from your architecture in under 2 minutes — then keep iterating. Change the diagram and the doc auto-syncs the affected sections, so your AI agent always has fresh context.
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

      {/* Unique Value Proposition */}
      <div className="tool-section tool-section-highlight">
        <h2>Why InfraSketch is Different</h2>
        <p className="tool-highlight-text">
          Other tools generate diagrams. InfraSketch generates a diagram <strong>and</strong> a real design doc — and keeps them in sync as you iterate. The diagram is for your team. The doc is for your AI agent. Both stay current automatically.
        </p>
      </div>

      {/* Doc Excerpt Gallery: shows what the generated content actually looks like */}
      <div className="tool-section">
        <h2>What a generated design doc actually looks like</h2>
        <p className="doc-excerpts-intro">
          Real screenshots from a generated URL-shortener doc. No mocks, no marketing fluff. Click any image to see it full-size.
        </p>
        <div className="doc-excerpts-grid">
          {DOC_EXCERPTS.map((excerpt, index) => {
            const screenshotIndex = SCREENSHOTS.findIndex(s => s.src === excerpt.src);
            return (
              <div key={index} className="doc-excerpt-card">
                <button
                  type="button"
                  className="doc-excerpt-image-button"
                  onClick={() => {
                    if (screenshotIndex >= 0) {
                      setCurrentScreenshot(screenshotIndex);
                      setLightboxOpen(true);
                    }
                  }}
                  aria-label={`View ${excerpt.title} full size`}
                >
                  <img
                    src={excerpt.src}
                    alt={excerpt.title}
                    className="doc-excerpt-image"
                    loading="lazy"
                  />
                </button>
                <h3 className="doc-excerpt-title">{excerpt.title}</h3>
                <p className="doc-excerpt-description">{excerpt.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Competitor Comparison Table */}
      <div className="tool-section">
        <h2>Feature Comparison</h2>
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>InfraSketch</th>
                <th>Eraser</th>
                <th>Lucidchart</th>
                <th>Miro</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row, index) => (
                <tr key={index}>
                  <td>{row.feature}</td>
                  <td className={row.infrasketch ? 'feature-yes' : 'feature-no'}>
                    {row.infrasketch ? '✓' : '✗'}
                  </td>
                  <td className={row.eraser ? 'feature-yes' : 'feature-no'}>
                    {row.eraser ? '✓' : '✗'}
                  </td>
                  <td className={row.lucidchart ? 'feature-yes' : 'feature-no'}>
                    {row.lucidchart ? '✓' : '✗'}
                  </td>
                  <td className={row.miro ? 'feature-yes' : 'feature-no'}>
                    {row.miro ? '✓' : '✗'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Features Grid */}
      <div className="tool-section tool-section-alt">
        <h2>Features</h2>
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

      {/* Document Sections */}
      <div className="tool-section">
        <h2>What's Included in Generated Documents</h2>
        <p>Every design document includes 12 comprehensive sections:</p>
        <div className="document-sections-grid">
          {DOCUMENT_SECTIONS.map((section, index) => (
            <div key={index} className="document-section-card">
              <div className="section-number">{index + 1}</div>
              <h3>{section.title}</h3>
              <p>{section.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works */}
      <div className="tool-section tool-section-alt">
        <h2>How It Works</h2>
        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">Create Your Diagram</h3>
            <p className="step-description">
              Describe your system in plain English and let InfraSketch generate your architecture diagram
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">Click "Create Design Doc"</h3>
            <p className="step-description">
              One click starts the AI documentation generation. Watch as 12 sections are written for you.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Review & Edit</h3>
            <p className="step-description">
              Review the generated document in the rich text editor. Make any changes or ask the AI to refine sections.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">4</div>
            <h3 className="step-title">Export & Share</h3>
            <p className="step-description">
              Export as PDF for presentations or Markdown for your wiki. The diagram is embedded in the document.
            </p>
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

      {/* Learn More Section */}
      <div className="tool-section tool-section-alt">
        <h2>Learn More</h2>
        <div className="learn-more-grid">
          <Link to="/tools/system-design-tool" className="learn-more-card">
            <span className="learn-more-icon">🎯</span>
            <h3>System Design Tool</h3>
            <p>Learn how to generate architecture diagrams from natural language descriptions.</p>
          </Link>
          <Link to="/blog/architecture-diagram-best-practices" className="learn-more-card">
            <span className="learn-more-icon">✏️</span>
            <h3>Diagram Best Practices</h3>
            <p>Create effective architecture diagrams that communicate clearly to your team.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">⚖️</span>
            <h3>Compare Tools</h3>
            <p>See how InfraSketch compares to other diagram and documentation tools.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Stop writing design docs. Start shipping.</h2>
        <p>Generate your first diagram and design doc in under 5 minutes. Watch them stay in sync as you iterate. Hand the doc to your AI agent and let it build.</p>
        <Link to="/" className="tool-cta-button">
          Start Free
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
