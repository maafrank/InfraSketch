import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

const COMPETITORS = [
  {
    name: "InfraSketch",
    highlight: true,
    features: {
      aiGeneration: true,
      naturalLanguage: true,
      chatRefinement: true,
      autoDocumentation: true,
      freeToStart: true,
      noInstall: true,
      realTimeCollab: false,
      cloudIcons: true
    },
    description: "AI-powered system design tool that generates architecture diagrams from plain English descriptions",
    bestFor: "Engineers who want to quickly sketch system architectures without manual diagramming",
    pricing: "Free tier available"
  },
  {
    name: "Lucidchart",
    highlight: false,
    features: {
      aiGeneration: false,
      naturalLanguage: false,
      chatRefinement: false,
      autoDocumentation: false,
      freeToStart: true,
      noInstall: true,
      realTimeCollab: true,
      cloudIcons: true
    },
    description: "Traditional diagramming tool with drag-and-drop interface and extensive shape libraries",
    bestFor: "Teams needing general-purpose diagramming with strong collaboration features",
    pricing: "Free tier, paid plans from $7.95/mo"
  },
  {
    name: "Eraser (DiagramGPT)",
    highlight: false,
    features: {
      aiGeneration: true,
      naturalLanguage: true,
      chatRefinement: false,
      autoDocumentation: false,
      freeToStart: true,
      noInstall: true,
      realTimeCollab: true,
      cloudIcons: true
    },
    description: "AI-powered diagramming with focus on technical documentation and whiteboarding",
    bestFor: "Teams wanting AI-assisted diagramming with whiteboard collaboration",
    pricing: "Free tier, paid plans from $10/mo"
  },
  {
    name: "Draw.io (Diagrams.net)",
    highlight: false,
    features: {
      aiGeneration: false,
      naturalLanguage: false,
      chatRefinement: false,
      autoDocumentation: false,
      freeToStart: true,
      noInstall: true,
      realTimeCollab: true,
      cloudIcons: true
    },
    description: "Free, open-source diagramming tool with extensive integrations",
    bestFor: "Cost-conscious teams needing a reliable, free diagramming solution",
    pricing: "Completely free"
  },
  {
    name: "Miro",
    highlight: false,
    features: {
      aiGeneration: false,
      naturalLanguage: false,
      chatRefinement: false,
      autoDocumentation: false,
      freeToStart: true,
      noInstall: true,
      realTimeCollab: true,
      cloudIcons: true
    },
    description: "Collaborative whiteboard platform with diagramming capabilities",
    bestFor: "Teams needing visual collaboration beyond just architecture diagrams",
    pricing: "Free tier, paid plans from $8/mo"
  }
];

const FEATURE_LABELS = {
  aiGeneration: "AI Diagram Generation",
  naturalLanguage: "Natural Language Input",
  chatRefinement: "Chat-Based Refinement",
  autoDocumentation: "Auto Design Docs",
  freeToStart: "Free to Start",
  noInstall: "No Install Required",
  realTimeCollab: "Real-Time Collaboration",
  cloudIcons: "Cloud Provider Icons"
};

export default function ComparePage() {
  const pageSchema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "Compare InfraSketch vs Lucidchart vs Eraser vs Draw.io",
    "description": "Compare AI architecture diagram tools. See how InfraSketch compares to Lucidchart, Eraser, Draw.io, and Miro for system design.",
    "url": "https://infrasketch.net/compare",
    "breadcrumb": {
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
        }
      ]
    }
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>Compare Architecture Diagram Tools | InfraSketch vs Lucidchart vs Eraser</title>
        <meta name="description" content="Compare AI architecture diagram tools. See how InfraSketch compares to Lucidchart, Eraser, Draw.io, and Miro for system design and architecture diagrams." />
        <meta name="keywords" content="lucidchart alternative, eraser alternative, draw.io alternative, architecture diagram tool comparison, AI diagram tools, system design tools comparison" />
        <link rel="canonical" href="https://infrasketch.net/compare" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="Compare Architecture Diagram Tools | InfraSketch vs Lucidchart vs Eraser" />
        <meta property="og:description" content="Compare AI architecture diagram tools. See how InfraSketch compares to Lucidchart, Eraser, Draw.io, and Miro." />
        <meta property="og:url" content="https://infrasketch.net/compare" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Compare Architecture Diagram Tools" />
        <meta name="twitter:description" content="Compare AI architecture diagram tools. InfraSketch vs Lucidchart vs Eraser vs Draw.io." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          Compare Architecture Diagram Tools
        </h1>
        <p className="tool-hero-subtitle">
          See how InfraSketch compares to other popular diagramming tools
          for system design and architecture diagrams.
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
                {COMPETITORS.map((tool, index) => (
                  <th key={index} className={tool.highlight ? 'highlight' : ''}>
                    {tool.name}
                    {tool.highlight && <span className="highlight-badge">You are here</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(FEATURE_LABELS).map(([key, label]) => (
                <tr key={key}>
                  <td className="feature-name">{label}</td>
                  {COMPETITORS.map((tool, index) => (
                    <td key={index} className={tool.highlight ? 'highlight' : ''}>
                      {tool.features[key] ? (
                        <span className="check">&#10003;</span>
                      ) : (
                        <span className="cross">&#10007;</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
              <tr>
                <td className="feature-name">Pricing</td>
                {COMPETITORS.map((tool, index) => (
                  <td key={index} className={tool.highlight ? 'highlight' : ''}>
                    {tool.pricing}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Tool Details */}
      <div className="tool-section tool-section-alt">
        <h2>Tool Details</h2>
        <div className="tool-details-grid">
          {COMPETITORS.map((tool, index) => (
            <div key={index} className={`tool-detail-card ${tool.highlight ? 'highlight' : ''}`}>
              <h3>{tool.name}</h3>
              <p className="tool-description">{tool.description}</p>
              <div className="tool-best-for">
                <strong>Best for:</strong> {tool.bestFor}
              </div>
              {tool.highlight && (
                <Link to="/" className="tool-try-button">
                  Try InfraSketch Free
                </Link>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Why InfraSketch */}
      <div className="tool-section">
        <h2>Why Choose InfraSketch?</h2>
        <div className="why-choose-grid">
          <div className="why-choose-card">
            <h3>AI-First Approach</h3>
            <p>
              Unlike traditional tools that add AI as an afterthought, InfraSketch was built
              from the ground up with AI at its core. Describe your system in plain English,
              and get a complete architecture diagram in seconds.
            </p>
          </div>
          <div className="why-choose-card">
            <h3>Conversational Refinement</h3>
            <p>
              Other tools generate a diagram and stop there. InfraSketch lets you chat with
              the AI to refine your design. Ask "add caching" or "what if we need 10x scale?"
              and watch your diagram evolve.
            </p>
          </div>
          <div className="why-choose-card">
            <h3>Auto Documentation</h3>
            <p>
              Generate comprehensive design documents automatically. Get component details,
              data flows, implementation notes, and architecture decisions. All from a
              single prompt.
            </p>
          </div>
          <div className="why-choose-card">
            <h3>System Design Focus</h3>
            <p>
              InfraSketch specializes in software architecture. Unlike general diagramming
              tools, we understand databases, APIs, load balancers, caches, and how they
              connect in real systems.
            </p>
          </div>
        </div>
      </div>

      {/* When to Use What */}
      <div className="tool-section tool-section-alt">
        <h2>When to Use What</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>Use InfraSketch when...</h3>
            <ul>
              <li>You want to quickly sketch a system architecture</li>
              <li>You're preparing for a system design interview</li>
              <li>You need auto-generated design documentation</li>
              <li>You want AI to suggest architecture patterns</li>
              <li>You prefer describing over dragging shapes</li>
            </ul>
          </div>
          <div className="when-to-use-card">
            <h3>Use traditional tools when...</h3>
            <ul>
              <li>You need pixel-perfect diagram control</li>
              <li>You're creating flowcharts or process diagrams</li>
              <li>You need extensive shape libraries beyond architecture</li>
              <li>Real-time collaboration is essential</li>
              <li>You prefer manual drag-and-drop interfaces</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Learn More Section */}
      <div className="tool-section">
        <h2>Learn More</h2>
        <div className="learn-more-grid">
          <Link to="/blog/best-ai-diagram-tools-2026" className="learn-more-card">
            <span className="learn-more-icon">🔍</span>
            <h3>Detailed AI Tools Comparison</h3>
            <p>In-depth comparison of InfraSketch, Eraser, ChatGPT+Mermaid, Whimsical, and Miro.</p>
          </Link>
          <Link to="/blog/architecture-diagram-best-practices" className="learn-more-card">
            <span className="learn-more-icon">✏️</span>
            <h3>Diagram Best Practices</h3>
            <p>Learn how to create effective architecture diagrams regardless of which tool you use.</p>
          </Link>
          <Link to="/blog/complete-guide-system-design" className="learn-more-card">
            <span className="learn-more-icon">📖</span>
            <h3>System Design Guide</h3>
            <p>Master system design concepts including scalability, caching, and architecture patterns.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Ready to Try AI-Powered System Design?</h2>
        <p>Create your first architecture diagram in seconds. No signup required to start.</p>
        <Link to="/" className="tool-cta-button">
          Try InfraSketch Free
        </Link>
      </div>

      <Footer />
    </div>
  );
}
