import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import '../App.css';

const DIAGRAM_TYPES = [
  {
    icon: "🏗️",
    title: "Microservices Architecture",
    description: "Design scalable microservices with API gateways, service mesh, and message queues"
  },
  {
    icon: "☁️",
    title: "Cloud Infrastructure",
    description: "Create AWS, GCP, or Azure architecture diagrams with proper cloud service icons"
  },
  {
    icon: "🔄",
    title: "Event-Driven Systems",
    description: "Visualize pub/sub patterns, event sourcing, and CQRS architectures"
  },
  {
    icon: "🗄️",
    title: "Database Architecture",
    description: "Design database schemas, sharding strategies, and replication topologies"
  },
  {
    icon: "⚡",
    title: "Real-Time Systems",
    description: "Create diagrams for WebSocket servers, streaming pipelines, and live updates"
  },
  {
    icon: "🔐",
    title: "Authentication Flows",
    description: "Visualize OAuth, JWT, SSO, and identity provider integrations"
  }
];

const HOW_AI_WORKS = [
  {
    step: "1",
    title: "Understand Requirements",
    description: "Our AI (powered by Claude) parses your natural language description to understand what you're building."
  },
  {
    step: "2",
    title: "Identify Components",
    description: "The AI identifies appropriate components: databases, caches, APIs, load balancers, queues, and services."
  },
  {
    step: "3",
    title: "Design Connections",
    description: "It determines how components should connect, considering data flow and system requirements."
  },
  {
    step: "4",
    title: "Generate Diagram",
    description: "A complete architecture diagram is generated with proper layout, labels, and component descriptions."
  }
];

const FAQS = [
  {
    question: "How does AI diagram generation work?",
    answer: "InfraSketch uses Claude AI to understand your system requirements from natural language. The AI identifies appropriate components (databases, caches, APIs, etc.), determines their connections, and generates a complete architecture diagram with proper layout and labels."
  },
  {
    question: "What AI model powers InfraSketch?",
    answer: "InfraSketch is powered by Claude AI from Anthropic. You can choose between Claude Haiku (faster, great for most diagrams) or Claude Sonnet (more detailed reasoning for complex systems)."
  },
  {
    question: "Can I edit the AI-generated diagram?",
    answer: "Yes. After generation, you can chat with the AI to request changes ('add a cache layer', 'remove the CDN'), manually add or delete nodes, and drag components to rearrange the layout."
  },
  {
    question: "Is this better than ChatGPT for diagrams?",
    answer: "ChatGPT can explain architectures but cannot create visual diagrams. InfraSketch generates actual interactive diagrams you can edit, export, and share. It combines AI understanding with visual diagram creation."
  },
  {
    question: "What makes this different from other AI diagram tools?",
    answer: "InfraSketch specializes in system architecture. Unlike general diagramming tools that add AI features, we built specifically for software engineers designing distributed systems, APIs, and cloud infrastructure."
  }
];

export default function AIDiagramGeneratorPage() {
  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "name": "InfraSketch AI Diagram Generator",
        "description": "AI-powered tool that generates architecture diagrams from natural language descriptions using Claude AI",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net/tools/ai-diagram-generator",
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
            "name": "AI Diagram Generator",
            "item": "https://infrasketch.net/tools/ai-diagram-generator"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page">
      <Helmet>
        <title>AI Diagram Generator | Create Architecture Diagrams with AI | InfraSketch</title>
        <meta name="description" content="Generate architecture diagrams with AI. Describe your system in plain English, get instant visual diagrams. Powered by Claude AI. Free to try." />
        <meta name="keywords" content="AI diagram generator, AI architecture diagram, diagram AI, Claude AI diagram, generate diagram from text, AI system design, automatic diagram generator" />
        <link rel="canonical" href="https://infrasketch.net/tools/ai-diagram-generator" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="AI Diagram Generator | Create Architecture Diagrams with AI" />
        <meta property="og:description" content="Generate architecture diagrams with AI. Describe your system in plain English, get instant visual diagrams." />
        <meta property="og:url" content="https://infrasketch.net/tools/ai-diagram-generator" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="AI Diagram Generator | Create Architecture Diagrams with AI" />
        <meta name="twitter:description" content="Generate architecture diagrams with AI. Describe your system in plain English, get instant visual diagrams." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      {/* Hero Section */}
      <div className="tool-hero-section">
        <Link to="/" className="tool-back-link">&larr; Back to InfraSketch</Link>
        <h1 className="tool-hero-title">
          AI Diagram Generator
        </h1>
        <p className="tool-hero-subtitle">
          Generate professional architecture diagrams from plain English descriptions.
          Powered by Claude AI. No design skills required.
        </p>
        <Link to="/" className="tool-cta-button">
          Generate Your First Diagram
        </Link>
      </div>

      {/* What Is Section */}
      <div className="tool-section">
        <h2>What is an AI Diagram Generator?</h2>
        <p>
          An AI diagram generator uses artificial intelligence to create visual diagrams from
          text descriptions. Instead of manually dragging shapes onto a canvas, you describe
          what you want to build, and the AI creates the diagram for you.
        </p>
        <p>
          InfraSketch specializes in software architecture diagrams. Our AI understands
          components like databases, APIs, load balancers, caches, and message queues.
          It knows how to connect them properly and generates professional-quality diagrams.
        </p>
      </div>

      {/* Diagram Types */}
      <div className="tool-section tool-section-alt">
        <h2>Types of Diagrams You Can Generate</h2>
        <div className="features-grid">
          {DIAGRAM_TYPES.map((type, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{type.icon}</div>
              <h3 className="feature-title">{type.title}</h3>
              <p className="feature-description">{type.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How AI Works */}
      <div className="tool-section">
        <h2>How the AI Creates Your Diagram</h2>
        <div className="steps-grid">
          {HOW_AI_WORKS.map((step, index) => (
            <div key={index} className="step-card">
              <div className="step-number">{step.step}</div>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-description">{step.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Example Prompts */}
      <div className="tool-section tool-section-alt">
        <h2>Example Prompts</h2>
        <div className="example-prompts-list">
          <div className="example-prompt-item">
            <span className="example-prompt-icon">🐦</span>
            <span>"Design Twitter's home timeline with feed generation, caching, and real-time updates"</span>
          </div>
          <div className="example-prompt-item">
            <span className="example-prompt-icon">🛒</span>
            <span>"Build an e-commerce checkout flow with cart, payments, inventory, and notifications"</span>
          </div>
          <div className="example-prompt-item">
            <span className="example-prompt-icon">📺</span>
            <span>"Create a video streaming platform like YouTube with upload, transcoding, and CDN"</span>
          </div>
          <div className="example-prompt-item">
            <span className="example-prompt-icon">🔗</span>
            <span>"Design a URL shortening service with analytics, high availability, and rate limiting"</span>
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
          <Link to="/blog/best-ai-diagram-tools-2026" className="learn-more-card">
            <span className="learn-more-icon">🔍</span>
            <h3>AI Diagram Tools Compared</h3>
            <p>Compare InfraSketch with other AI-powered diagramming tools on the market.</p>
          </Link>
          <Link to="/blog/architecture-diagram-best-practices" className="learn-more-card">
            <span className="learn-more-icon">✏️</span>
            <h3>Diagram Best Practices</h3>
            <p>Learn how to create effective architecture diagrams that communicate clearly.</p>
          </Link>
          <Link to="/compare" className="learn-more-card">
            <span className="learn-more-icon">⚖️</span>
            <h3>Compare Tools</h3>
            <p>See how InfraSketch compares to Lucidchart, Eraser, Draw.io, and Miro.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Ready to Generate Your Diagram?</h2>
        <p>Describe your system and watch the AI create your architecture. Free to try.</p>
        <Link to="/" className="tool-cta-button">
          Try AI Diagram Generator
        </Link>
      </div>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">AI-powered system design</p>
          </div>
          <div className="footer-links">
            <Link to="/about">About</Link>
            <Link to="/blog">Blog</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="/tools/system-design-tool">System Design Tool</Link>
            <Link to="/tools/ai-diagram-generator">AI Diagram Generator</Link>
            <Link to="/compare">Compare</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
            <Link to="/contact">Contact</Link>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2025 InfraSketch. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
