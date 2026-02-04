import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

const COMPARISON_DATA = [
  { feature: "AI Diagram Generation", infrasketch: true, eraser: true },
  { feature: "Natural Language Input", infrasketch: true, eraser: true },
  { feature: "Auto Design Document Generation", infrasketch: true, eraser: false },
  { feature: "Chat-Based Refinement", infrasketch: true, eraser: false },
  { feature: "Real-Time Collaboration", infrasketch: false, eraser: true },
  { feature: "Whiteboard Mode", infrasketch: false, eraser: true },
  { feature: "Cloud Provider Icons", infrasketch: true, eraser: true },
  { feature: "Export to PNG", infrasketch: true, eraser: true },
  { feature: "Export to PDF", infrasketch: true, eraser: true },
  { feature: "Markdown Export", infrasketch: true, eraser: true },
  { feature: "Free Tier", infrasketch: true, eraser: true }
];

const FAQS = [
  {
    question: "What is Eraser DiagramGPT?",
    answer: "Eraser is a technical documentation and diagramming tool that includes DiagramGPT, an AI feature that generates diagrams from text descriptions. It focuses on whiteboarding and real-time collaboration for engineering teams."
  },
  {
    question: "How does InfraSketch compare to Eraser?",
    answer: "Both tools offer AI diagram generation. The key difference is that InfraSketch generates comprehensive design documents in addition to diagrams, and offers chat-based refinement to iterate on your architecture. Eraser focuses more on whiteboarding and team collaboration."
  },
  {
    question: "Which tool is better for system design interviews?",
    answer: "InfraSketch is optimized for system design practice. You can describe systems, get instant diagrams, refine through chat, and generate design documents. This workflow mirrors actual interview scenarios better than whiteboard-focused tools."
  },
  {
    question: "Does Eraser generate design documents?",
    answer: "No, Eraser focuses on diagrams and whiteboard collaboration. InfraSketch is the only AI tool that generates both architecture diagrams AND comprehensive design documents from the same input."
  },
  {
    question: "Can I migrate from Eraser to InfraSketch?",
    answer: "While there is no direct import feature, you can recreate any system architecture by describing it in InfraSketch. The AI will generate the diagram and you can refine it through chat to match your existing design."
  }
];

export default function InfraSketchVsEraserPage() {
  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "name": "InfraSketch vs Eraser - AI Diagram Tool Comparison",
        "description": "Compare InfraSketch and Eraser DiagramGPT for AI-powered architecture diagrams. See which tool is best for system design.",
        "url": "https://infrasketch.net/compare/eraser"
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
            "name": "InfraSketch vs Eraser",
            "item": "https://infrasketch.net/compare/eraser"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>InfraSketch vs Eraser | AI Diagram Tool Comparison 2026</title>
        <meta name="description" content="Compare InfraSketch and Eraser DiagramGPT for AI-powered architecture diagrams. InfraSketch generates design documents, Eraser focuses on whiteboarding. See the full comparison." />
        <meta name="keywords" content="infrasketch vs eraser, eraser alternative, diagramgpt alternative, ai diagram generator comparison, eraser diagramgpt vs infrasketch" />
        <link rel="canonical" href="https://infrasketch.net/compare/eraser" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="InfraSketch vs Eraser | AI Diagram Tool Comparison" />
        <meta property="og:description" content="Compare InfraSketch and Eraser DiagramGPT for AI-powered architecture diagrams. See which tool is best for your needs." />
        <meta property="og:url" content="https://infrasketch.net/compare/eraser" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="InfraSketch vs Eraser | AI Diagram Tool Comparison" />
        <meta name="twitter:description" content="Compare InfraSketch and Eraser DiagramGPT for AI-powered architecture diagrams." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          InfraSketch vs Eraser
        </h1>
        <p className="tool-hero-subtitle">
          Both tools offer AI diagram generation. InfraSketch adds auto design documents and chat refinement.
          Eraser focuses on whiteboarding and team collaboration.
        </p>
      </div>

      {/* Key Difference */}
      <div className="tool-section tool-section-highlight">
        <h2>The Key Difference</h2>
        <p className="tool-highlight-text">
          Eraser generates diagrams. InfraSketch generates diagrams <strong>and</strong> comprehensive design documents.
          InfraSketch also lets you refine your architecture through natural conversation, while Eraser is more focused on
          visual collaboration and whiteboarding.
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
                <th>Eraser</th>
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
                    {row.eraser ? (
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
            <h3>Eraser</h3>
            <p className="tool-tagline">Technical Diagramming and Whiteboarding</p>
            <ul className="pros-list">
              <li>DiagramGPT for AI diagram generation</li>
              <li>Real-time team collaboration</li>
              <li>Whiteboard mode for brainstorming</li>
              <li>Technical documentation focus</li>
              <li>Multiple diagram types (sequence, ER, etc.)</li>
            </ul>
            <div className="best-for">
              <strong>Best for:</strong> Teams needing whiteboard collaboration with AI-assisted diagramming
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
              <li>You want to iterate on architecture through conversation</li>
              <li>You're preparing for system design interviews</li>
              <li>You want comprehensive design docs without manual writing</li>
              <li>You prefer describing systems over visual whiteboarding</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Choose Eraser when...</h3>
            <ul>
              <li>Real-time team collaboration is essential</li>
              <li>You need whiteboard brainstorming features</li>
              <li>You're creating multiple diagram types (sequence, ER)</li>
              <li>Your team already uses Eraser for documentation</li>
              <li>You prefer visual collaboration over AI refinement</li>
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
          <Link to="/compare/lucidchart" className="learn-more-card">
            <span className="learn-more-icon">📊</span>
            <h3>InfraSketch vs Lucidchart</h3>
            <p>Compare AI-powered generation with traditional drag-and-drop diagramming.</p>
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

      <Footer />
    </div>
  );
}
