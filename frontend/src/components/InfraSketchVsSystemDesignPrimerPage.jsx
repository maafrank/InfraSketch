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
  { feature: "Visual Architecture Diagrams", infrasketch: true, primer: false },
  { feature: "AI-Powered Generation", infrasketch: true, primer: false },
  { feature: "Interactive Refinement", infrasketch: true, primer: false },
  { feature: "Auto Design Documents", infrasketch: true, primer: false },
  { feature: "System Design Concepts", infrasketch: true, primer: true },
  { feature: "Interview Practice Problems", infrasketch: true, primer: true },
  { feature: "Code Examples", infrasketch: false, primer: true },
  { feature: "Open Source", infrasketch: false, primer: true },
  { feature: "Community Contributions", infrasketch: false, primer: true },
  { feature: "Export to PNG/PDF", infrasketch: true, primer: false },
  { feature: "Free to Use", infrasketch: true, primer: true }
];

const FAQS = [
  {
    question: "What is System Design Primer?",
    answer: "System Design Primer is a popular open-source GitHub repository created by Donne Martin with over 250,000 stars. It is a comprehensive collection of system design concepts, patterns, and interview questions presented as text and static diagrams. It is one of the most widely used resources for learning system design fundamentals."
  },
  {
    question: "How does InfraSketch compare to System Design Primer?",
    answer: "System Design Primer is a learning resource with text-based explanations and static diagrams. InfraSketch is an interactive tool that generates architecture diagrams from natural language and lets you refine them through conversation. They complement each other well: learn concepts from System Design Primer, then practice building architectures with InfraSketch."
  },
  {
    question: "Can I practice System Design Primer problems in InfraSketch?",
    answer: "Yes. System Design Primer covers problems like designing Twitter, a URL shortener, a web crawler, and more. You can take any of these problems and describe them in InfraSketch to generate the architecture diagram instantly. Then use chat to explore trade-offs, add components, or consider scale."
  },
  {
    question: "Which should I use for interview preparation?",
    answer: "Use both. Start with System Design Primer to learn the fundamental concepts, patterns, and vocabulary. Then use InfraSketch to practice applying those concepts by building actual architecture diagrams. This combination of theory and hands-on practice is the most effective preparation strategy."
  },
  {
    question: "Does InfraSketch cover ML and AI system design?",
    answer: "Yes. While System Design Primer focuses primarily on traditional system design (databases, caching, load balancing), InfraSketch can generate architectures for ML pipelines, LLM applications, RAG systems, recommendation engines, and other AI systems. This makes it valuable for the growing number of ML system design interviews."
  }
];

export default function InfraSketchVsSystemDesignPrimerPage() {
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
        "name": "InfraSketch vs System Design Primer - Interactive Tool vs Learning Resource",
        "description": "Compare InfraSketch and System Design Primer for system design practice. InfraSketch generates interactive diagrams, System Design Primer teaches concepts.",
        "url": "https://infrasketch.net/compare/system-design-primer"
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
            "name": "InfraSketch vs System Design Primer",
            "item": "https://infrasketch.net/compare/system-design-primer"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs System Design Primer | Interactive Diagrams vs Static Learning</title>
        <meta name="description" content="Compare InfraSketch and System Design Primer (GitHub). InfraSketch generates interactive architecture diagrams with AI. System Design Primer teaches concepts with text. Use both for the best interview prep." />
        <meta name="keywords" content="system design primer alternative, system design primer vs infrasketch, system design practice tool, system design interview tool, AI system design github" />
        <link rel="canonical" href="https://infrasketch.net/compare/system-design-primer" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs System Design Primer | Interactive Diagrams vs Static Learning" />
        <meta property="og:description" content="Compare InfraSketch and System Design Primer for system design practice and interview preparation." />
        <meta property="og:url" content="https://infrasketch.net/compare/system-design-primer" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs System Design Primer" />
        <meta name="twitter:description" content="Compare InfraSketch and System Design Primer for system design practice." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs System Design Primer
        </h1>
        <p className="tool-hero-subtitle">
          System Design Primer teaches you the concepts.
          InfraSketch lets you practice them visually with AI-generated architecture diagrams.
          Use both for the most effective interview prep.
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
          System Design Primer is a <strong>learning resource</strong> with text explanations and static diagrams.
          InfraSketch is an <strong>interactive tool</strong> that generates architecture diagrams from natural language
          and lets you refine them through conversation. Think of it as the difference between reading about system
          design and actually building system designs.
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
                <th>System Design Primer</th>
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
                    {row.primer ? (
                      <span className="check">&#10003;</span>
                    ) : (
                      <span className="cross">&#10007;</span>
                    )}
                  </td>
                </tr>
              ))}
              <tr>
                <td className="feature-name">Format</td>
                <td className="highlight">Interactive web app</td>
                <td>GitHub repository (text + images)</td>
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
            <p className="tool-tagline">AI-Powered Interactive System Design Tool</p>
            <ul className="pros-list">
              <li><strong>Unique:</strong> Generates diagrams from natural language</li>
              <li><strong>Unique:</strong> Auto-generates comprehensive design documents</li>
              <li><strong>Unique:</strong> Chat-based refinement of architectures</li>
              <li>Supports ML/AI system design (LLM, RAG, ML pipelines)</li>
              <li>Export to PNG, PDF, and Markdown</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Hands-on practice building actual architecture diagrams
            </div>
            <Link to="/" className="tool-try-button">Try InfraSketch Free</Link>
          </div>
          <div className="side-by-side-card">
            <h3>System Design Primer</h3>
            <p className="tool-tagline">Open-Source System Design Learning Resource</p>
            <ul className="pros-list">
              <li>250,000+ GitHub stars (massive community)</li>
              <li>Comprehensive concept coverage (databases, caching, etc.)</li>
              <li>Interview question walkthroughs</li>
              <li>Code examples and Anki flashcards</li>
              <li>Completely free and open-source</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Learning system design concepts and fundamentals
            </div>
          </div>
        </div>
      </div>

      {/* When to Use */}
      <div className="tool-section">
        <h2>When to Use Each</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>Use InfraSketch when...</h3>
            <ul>
              <li>You want to practice building actual architecture diagrams</li>
              <li>You need to quickly visualize a system design idea</li>
              <li>You want auto-generated design documentation</li>
              <li>You are designing ML/AI system architectures</li>
              <li>You prefer interactive, visual learning over reading</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Use System Design Primer when...</h3>
            <ul>
              <li>You are learning system design concepts for the first time</li>
              <li>You want detailed text explanations of each concept</li>
              <li>You need flashcards for memorizing key patterns</li>
              <li>You want to study offline (GitHub/PDF)</li>
              <li>You prefer reading and self-study over interactive tools</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Best Strategy */}
      <div className="tool-section tool-section-alt">
        <h2>The Best Interview Prep Strategy: Use Both</h2>
        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">Learn Concepts</h3>
            <p className="step-description">
              Read System Design Primer to understand fundamental concepts: load balancing, caching, databases, message queues, and architectural patterns.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">Practice Visually</h3>
            <p className="step-description">
              Take each problem from System Design Primer and build the architecture in InfraSketch. Describe the system and refine through chat.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Generate Documentation</h3>
            <p className="step-description">
              Use InfraSketch to generate design documents for each problem. Review them to identify gaps in your design thinking.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">4</div>
            <h3 className="step-title">Iterate and Improve</h3>
            <p className="step-description">
              Use the chat to explore trade-offs, add scaling considerations, and refine your architecture until you can explain every decision.
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

      {/* Learn More */}
      <div className="tool-section tool-section-alt">
        <h2>Related Resources</h2>
        <div className="learn-more-grid">
          <Link to="/compare/bytebytego" className="learn-more-card">
            <span className="learn-more-icon">📚</span>
            <h3>InfraSketch vs ByteByteGo</h3>
            <p>Compare InfraSketch with Alex Xu's ByteByteGo system design course.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">📊</span>
            <h3>Full Tool Comparison</h3>
            <p>Compare InfraSketch with Lucidchart, Eraser, Draw.io, and Miro.</p>
          </Link>
          <Link to="/blog/system-design-interview-prep-practice" className="learn-more-card">
            <span className="learn-more-icon">📋</span>
            <h3>Interview Prep Guide</h3>
            <p>Complete system design interview preparation guide with study plan.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Practice System Design Visually</h2>
        <p>Turn System Design Primer concepts into interactive architecture diagrams. No signup required.</p>
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
