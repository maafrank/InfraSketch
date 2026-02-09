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
  { feature: "AI Diagram Generation", infrasketch: true, bbg: false },
  { feature: "Natural Language Input", infrasketch: true, bbg: false },
  { feature: "Interactive Refinement", infrasketch: true, bbg: false },
  { feature: "Auto Design Documents", infrasketch: true, bbg: false },
  { feature: "Visual Explanations", infrasketch: true, bbg: true },
  { feature: "Interview Questions", infrasketch: true, bbg: true },
  { feature: "Video Content", infrasketch: false, bbg: true },
  { feature: "Newsletter", infrasketch: false, bbg: true },
  { feature: "Books (System Design Vol 1 & 2)", infrasketch: false, bbg: true },
  { feature: "ML/AI System Design", infrasketch: true, bbg: true },
  { feature: "Free Tier", infrasketch: true, bbg: true }
];

const FAQS = [
  {
    question: "What is ByteByteGo?",
    answer: "ByteByteGo is a system design learning platform created by Alex Xu, author of the System Design Interview books (Vol 1 and Vol 2). It offers a newsletter, course content, and visual explanations of system design concepts and real-world architectures."
  },
  {
    question: "How does InfraSketch compare to ByteByteGo?",
    answer: "ByteByteGo is a learning platform with pre-made visual explanations and courses. InfraSketch is an interactive tool where you generate your own architecture diagrams from descriptions. ByteByteGo teaches you how systems work; InfraSketch lets you practice designing systems yourself."
  },
  {
    question: "Which is better for system design interview prep?",
    answer: "They serve different purposes. ByteByteGo is excellent for learning concepts and studying real-world architectures through its books and visual content. InfraSketch is better for hands-on practice, where you describe systems and build diagrams interactively. The most effective approach is to learn from ByteByteGo and practice with InfraSketch."
  },
  {
    question: "Does ByteByteGo generate diagrams?",
    answer: "No. ByteByteGo provides pre-made visual explanations of system design concepts. InfraSketch generates custom architecture diagrams from your natural language descriptions, letting you build any system you can describe and refine it through conversation."
  },
  {
    question: "Can InfraSketch help with Alex Xu's system design problems?",
    answer: "Yes. You can take any problem from the System Design Interview books (designing a chat system, rate limiter, news feed, etc.) and build the architecture in InfraSketch. This gives you hands-on practice with the exact problems covered in the books."
  }
];

export default function InfraSketchVsByteByteGoPage() {
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
        "name": "InfraSketch vs ByteByteGo - Interactive Tool vs Learning Platform",
        "description": "Compare InfraSketch and ByteByteGo for system design. InfraSketch generates interactive diagrams, ByteByteGo teaches with visual explanations and courses.",
        "url": "https://infrasketch.net/compare/bytebytego"
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
            "name": "InfraSketch vs ByteByteGo",
            "item": "https://infrasketch.net/compare/bytebytego"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs ByteByteGo | System Design Tool vs Course Comparison</title>
        <meta name="description" content="Compare InfraSketch and ByteByteGo (Alex Xu) for system design interview preparation. InfraSketch generates interactive diagrams, ByteByteGo teaches with visual explanations." />
        <meta name="keywords" content="bytebytego alternative, bytebytego vs infrasketch, system design interview prep, alex xu system design, system design course comparison" />
        <link rel="canonical" href="https://infrasketch.net/compare/bytebytego" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs ByteByteGo | System Design Tool vs Course" />
        <meta property="og:description" content="Compare InfraSketch and ByteByteGo for system design preparation. Interactive diagrams vs visual learning." />
        <meta property="og:url" content="https://infrasketch.net/compare/bytebytego" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs ByteByteGo" />
        <meta name="twitter:description" content="Compare InfraSketch and ByteByteGo for system design interview preparation." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs ByteByteGo
        </h1>
        <p className="tool-hero-subtitle">
          ByteByteGo teaches system design with visual explanations and courses.
          InfraSketch lets you build system designs hands-on with AI-generated diagrams.
          Combine both for the most effective interview preparation.
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
          ByteByteGo teaches system design through <strong>curated visual content</strong> and Alex Xu's books.
          InfraSketch lets you <strong>practice building systems yourself</strong> with AI-generated diagrams
          and auto-generated design documents. One teaches the theory, the other provides hands-on practice.
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
                <th>ByteByteGo</th>
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
                    {row.bbg ? (
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
                <td>Free newsletter, paid course from $79/yr</td>
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
              <li><strong>Unique:</strong> Auto-generates design documents</li>
              <li><strong>Unique:</strong> Conversational architecture refinement</li>
              <li>Supports ML/AI, LLM, and traditional system design</li>
              <li>Export to PNG, PDF, and Markdown</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Hands-on practice building architecture diagrams
            </div>
            <Link to="/" className="tool-try-button">Try InfraSketch Free</Link>
          </div>
          <div className="side-by-side-card">
            <h3>ByteByteGo</h3>
            <p className="tool-tagline">System Design Learning Platform by Alex Xu</p>
            <ul className="pros-list">
              <li>Beautifully illustrated visual explanations</li>
              <li>System Design Interview books (Vol 1 and 2)</li>
              <li>Weekly newsletter with real-world case studies</li>
              <li>Video walkthroughs of design problems</li>
              <li>Large community of system design learners</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Learning system design concepts through curated visual content
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
              <li>You want hands-on practice designing systems</li>
              <li>You need to quickly diagram an architecture idea</li>
              <li>You want auto-generated design documentation</li>
              <li>You are working on ML/AI system designs</li>
              <li>You want to explore trade-offs through conversation</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Use ByteByteGo when...</h3>
            <ul>
              <li>You are learning system design from scratch</li>
              <li>You prefer curated, visual explanations</li>
              <li>You want structured course material with books</li>
              <li>You enjoy learning through newsletters and videos</li>
              <li>You want to study real-world system architectures</li>
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
          <Link to="/compare/system-design-primer" className="learn-more-card">
            <span className="learn-more-icon">📁</span>
            <h3>InfraSketch vs System Design Primer</h3>
            <p>Compare InfraSketch with the popular open-source GitHub repository.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">📊</span>
            <h3>Full Tool Comparison</h3>
            <p>Compare InfraSketch with Lucidchart, Eraser, Draw.io, and Miro.</p>
          </Link>
          <Link to="/blog/ml-system-design-patterns" className="learn-more-card">
            <span className="learn-more-icon">🧠</span>
            <h3>ML System Design Patterns</h3>
            <p>Learn machine learning system design patterns for production systems.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Practice System Design Hands-On</h2>
        <p>Turn ByteByteGo concepts into interactive architecture diagrams. No signup required.</p>
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
