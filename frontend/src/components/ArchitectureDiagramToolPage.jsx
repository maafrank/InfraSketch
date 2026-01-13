import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import '../App.css';

const COMPONENT_TYPES = [
  { icon: "🗄️", name: "Databases", description: "PostgreSQL, MongoDB, Redis, DynamoDB" },
  { icon: "⚡", name: "Caches", description: "Redis, Memcached, CDN caches" },
  { icon: "🔌", name: "APIs", description: "REST APIs, GraphQL, gRPC services" },
  { icon: "⚖️", name: "Load Balancers", description: "NGINX, HAProxy, AWS ALB" },
  { icon: "📬", name: "Message Queues", description: "Kafka, RabbitMQ, SQS" },
  { icon: "🌐", name: "CDNs", description: "CloudFront, Cloudflare, Fastly" },
  { icon: "🔐", name: "Auth Services", description: "OAuth, JWT, Identity providers" },
  { icon: "📊", name: "Analytics", description: "Monitoring, logging, metrics" }
];

const CLOUD_PLATFORMS = [
  {
    name: "AWS",
    description: "Design architectures using EC2, Lambda, S3, RDS, DynamoDB, SQS, and more AWS services",
    icon: "☁️"
  },
  {
    name: "Google Cloud",
    description: "Create GCP architectures with Compute Engine, Cloud Functions, BigQuery, and Pub/Sub",
    icon: "🌩️"
  },
  {
    name: "Microsoft Azure",
    description: "Build Azure solutions with VMs, Functions, Cosmos DB, and Service Bus",
    icon: "💠"
  },
  {
    name: "Multi-Cloud",
    description: "Design hybrid architectures spanning multiple cloud providers",
    icon: "🔗"
  }
];

const FAQS = [
  {
    question: "What is an architecture diagram tool?",
    answer: "An architecture diagram tool helps you visualize the structure of software systems. It shows components (databases, servers, APIs) and how they connect. Architecture diagrams are essential for planning, documentation, and team communication."
  },
  {
    question: "What components can I add to my diagram?",
    answer: "InfraSketch supports databases, caches, APIs, load balancers, message queues, CDNs, gateways, storage services, and custom components. The AI automatically suggests appropriate components based on your system description."
  },
  {
    question: "Can I create AWS architecture diagrams?",
    answer: "Yes. InfraSketch understands AWS services and can generate diagrams with EC2, Lambda, S3, RDS, DynamoDB, SQS, SNS, CloudFront, and other AWS components. Just describe your AWS architecture in plain English."
  },
  {
    question: "How do I export my architecture diagram?",
    answer: "You can export diagrams as PNG images (free), PDF documents with embedded diagrams, or Markdown files. Premium users can also generate comprehensive design documents with component details and implementation notes."
  },
  {
    question: "Is this suitable for technical documentation?",
    answer: "Yes. InfraSketch generates clean, professional diagrams ideal for technical documentation. The auto-generated design documents include architecture diagrams, component descriptions, data flows, and implementation recommendations."
  }
];

export default function ArchitectureDiagramToolPage() {
  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "name": "InfraSketch Architecture Diagram Tool",
        "description": "Create professional software architecture diagrams with AI. Supports AWS, GCP, Azure, and custom architectures.",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net/tools/architecture-diagram-tool",
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
            "name": "Architecture Diagram Tool",
            "item": "https://infrasketch.net/tools/architecture-diagram-tool"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page">
      <Helmet>
        <title>Architecture Diagram Tool | Software Architecture Diagrams | InfraSketch</title>
        <meta name="description" content="Create software architecture diagrams with AI. Design AWS, GCP, Azure, and microservices architectures. Generate diagrams from plain English descriptions." />
        <meta name="keywords" content="architecture diagram tool, software architecture diagram, AWS architecture diagram, cloud architecture diagram, microservices diagram, system architecture visualization" />
        <link rel="canonical" href="https://infrasketch.net/tools/architecture-diagram-tool" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="Architecture Diagram Tool | Software Architecture Diagrams" />
        <meta property="og:description" content="Create software architecture diagrams with AI. Design AWS, GCP, Azure, and microservices architectures." />
        <meta property="og:url" content="https://infrasketch.net/tools/architecture-diagram-tool" />
        <meta property="og:image" content="https://infrasketch.net/FullAppWithDesignDoc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Architecture Diagram Tool | Software Architecture Diagrams" />
        <meta name="twitter:description" content="Create software architecture diagrams with AI. Design AWS, GCP, Azure, and microservices architectures." />
        <meta name="twitter:image" content="https://infrasketch.net/FullAppWithDesignDoc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      {/* Hero Section */}
      <div className="tool-hero-section">
        <Link to="/" className="tool-back-link">&larr; Back to InfraSketch</Link>
        <h1 className="tool-hero-title">
          Architecture Diagram Tool
        </h1>
        <p className="tool-hero-subtitle">
          Create professional software architecture diagrams in seconds.
          Describe your system, and watch the AI generate your architecture.
        </p>
        <Link to="/" className="tool-cta-button">
          Create Your Diagram
        </Link>
      </div>

      {/* What Is Section */}
      <div className="tool-section">
        <h2>What is an Architecture Diagram?</h2>
        <p>
          An architecture diagram is a visual representation of a software system's structure.
          It shows the components that make up a system (databases, servers, APIs, etc.) and
          how they interact with each other.
        </p>
        <p>
          Good architecture diagrams help teams understand complex systems, onboard new developers,
          plan changes, and communicate technical decisions. InfraSketch makes creating these
          diagrams fast and easy with AI-powered generation.
        </p>
      </div>

      {/* Component Types */}
      <div className="tool-section tool-section-alt">
        <h2>Supported Components</h2>
        <div className="component-grid">
          {COMPONENT_TYPES.map((component, index) => (
            <div key={index} className="component-card">
              <span className="component-icon">{component.icon}</span>
              <div className="component-info">
                <h3>{component.name}</h3>
                <p>{component.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cloud Platforms */}
      <div className="tool-section">
        <h2>Cloud Architecture Support</h2>
        <p className="section-intro">
          InfraSketch understands major cloud platforms and can generate appropriate architecture diagrams:
        </p>
        <div className="cloud-grid">
          {CLOUD_PLATFORMS.map((platform, index) => (
            <div key={index} className="cloud-card">
              <div className="cloud-icon">{platform.icon}</div>
              <h3>{platform.name}</h3>
              <p>{platform.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="tool-section tool-section-alt">
        <h2>Key Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🎨</div>
            <h3 className="feature-title">Auto Layout</h3>
            <p className="feature-description">Diagrams are automatically arranged for clarity. No manual positioning required.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔗</div>
            <h3 className="feature-title">Smart Connections</h3>
            <p className="feature-description">AI determines how components should connect based on your description.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📝</div>
            <h3 className="feature-title">Component Descriptions</h3>
            <p className="feature-description">Each component includes detailed descriptions and technology choices.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📦</div>
            <h3 className="feature-title">Collapsible Groups</h3>
            <p className="feature-description">Organize complex systems by grouping related components together.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3 className="feature-title">Chat Refinement</h3>
            <p className="feature-description">Click any component and chat with AI to modify or understand it better.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📤</div>
            <h3 className="feature-title">Multiple Exports</h3>
            <p className="feature-description">Export as PNG, PDF, or Markdown. Generate full design documents.</p>
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
        <h2>Learn More About Architecture Diagrams</h2>
        <div className="learn-more-grid">
          <Link to="/blog/architecture-diagram-best-practices" className="learn-more-card">
            <span className="learn-more-icon">✏️</span>
            <h3>Diagram Best Practices</h3>
            <p>Learn the C4 model, notation conventions, and tips for creating clear diagrams.</p>
          </Link>
          <Link to="/blog/complete-guide-system-design" className="learn-more-card">
            <span className="learn-more-icon">📖</span>
            <h3>Complete System Design Guide</h3>
            <p>Master system design fundamentals and advanced patterns used by top companies.</p>
          </Link>
          <Link to="/blog/best-ai-diagram-tools-2026" className="learn-more-card">
            <span className="learn-more-icon">🔍</span>
            <h3>AI Diagram Tools Compared</h3>
            <p>See how InfraSketch compares to other AI-powered diagramming tools.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Ready to Create Your Architecture Diagram?</h2>
        <p>Describe your system and get a professional diagram in seconds. Free to try.</p>
        <Link to="/" className="tool-cta-button">
          Start Creating
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
