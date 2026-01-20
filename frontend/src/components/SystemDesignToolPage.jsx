import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

const FEATURES = [
  {
    icon: "🎯",
    title: "Natural Language Input",
    description: "Describe your system in plain English. No drag-and-drop, no blank canvas paralysis."
  },
  {
    icon: "🤖",
    title: "AI-Powered Generation",
    description: "Claude AI understands your requirements and generates complete architecture diagrams in seconds."
  },
  {
    icon: "💬",
    title: "Conversational Refinement",
    description: "Chat with the AI to modify your design. Ask 'add caching' or 'what if we need 10x scale?'"
  },
  {
    icon: "📄",
    title: "Auto Documentation",
    description: "Generate comprehensive design docs with component details, data flows, and implementation notes."
  },
  {
    icon: "🔄",
    title: "Real-Time Updates",
    description: "Watch your diagram evolve as you describe changes. No manual re-drawing required."
  },
  {
    icon: "📤",
    title: "Export Anywhere",
    description: "Export to PNG, PDF, or Markdown. Share with your team or use in presentations."
  }
];

const USE_CASES = [
  {
    title: "System Design Interviews",
    description: "Practice common interview problems like designing Twitter, Netflix, or Uber. Get instant feedback on your architecture decisions.",
    icon: "🎓"
  },
  {
    title: "Technical Documentation",
    description: "Create architecture diagrams for your documentation. Keep them in sync with your evolving system.",
    icon: "📚"
  },
  {
    title: "Rapid Prototyping",
    description: "Sketch out ideas quickly before committing to code. Explore different architectural approaches.",
    icon: "⚡"
  },
  {
    title: "Team Communication",
    description: "Share clear visual representations of your systems. Get everyone on the same page.",
    icon: "👥"
  }
];

const FAQS = [
  {
    question: "What is a system design tool?",
    answer: "A system design tool helps software engineers and architects visualize the structure of software systems. It shows components like databases, APIs, load balancers, and caches, plus how they connect. InfraSketch uses AI to generate these diagrams from plain English descriptions."
  },
  {
    question: "How is InfraSketch different from Lucidchart or Draw.io?",
    answer: "Traditional tools require manual drag-and-drop. InfraSketch generates diagrams from natural language descriptions. Describe what you want, and our AI creates the architecture for you. Then chat to refine it."
  },
  {
    question: "Can I use this for system design interviews?",
    answer: "Yes. InfraSketch is ideal for interview prep. Practice designing Twitter, Netflix, or any system. The AI helps you think through scalability, trade-offs, and component choices."
  },
  {
    question: "What types of diagrams can I create?",
    answer: "InfraSketch supports microservices architectures, cloud infrastructure (AWS, GCP, Azure), API designs, database schemas, event-driven systems, and more. Any system you can describe, you can diagram."
  },
  {
    question: "Is there a free tier?",
    answer: "Yes. The free tier includes diagram generation, AI chat refinement, and PNG export. Premium features include PDF export, design document generation, and session history."
  }
];

export default function SystemDesignToolPage() {
  // Schema.org structured data
  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "name": "InfraSketch System Design Tool",
        "description": "AI-powered system design tool that generates architecture diagrams from natural language descriptions",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net/tools/system-design-tool",
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
            "name": "System Design Tool",
            "item": "https://infrasketch.net/tools/system-design-tool"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page">
      <Helmet>
        <title>System Design Tool | AI-Powered Architecture Diagrams | InfraSketch</title>
        <meta name="description" content="Free AI system design tool. Describe your architecture in plain English, get instant diagrams. Perfect for system design interviews, documentation, and rapid prototyping." />
        <meta name="keywords" content="system design tool, system architecture tool, software architecture diagram, system design interview, architecture diagram generator, microservices design tool" />
        <link rel="canonical" href="https://infrasketch.net/tools/system-design-tool" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="System Design Tool | AI-Powered Architecture Diagrams" />
        <meta property="og:description" content="Free AI system design tool. Describe your architecture in plain English, get instant diagrams." />
        <meta property="og:url" content="https://infrasketch.net/tools/system-design-tool" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="System Design Tool | AI-Powered Architecture Diagrams" />
        <meta name="twitter:description" content="Free AI system design tool. Describe your architecture in plain English, get instant diagrams." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          System Design Tool
        </h1>
        <p className="tool-hero-subtitle">
          Describe your system in plain English. Get a complete architecture diagram in seconds.
          No drag-and-drop. No blank canvas paralysis.
        </p>
        <Link to="/" className="tool-cta-button">
          Try It Free
        </Link>
      </div>

      {/* What Is Section */}
      <div className="tool-section">
        <h2>What is a System Design Tool?</h2>
        <p>
          A system design tool helps software engineers visualize and plan the structure of
          software systems. It shows how components like databases, APIs, load balancers,
          caches, and services connect to form a complete architecture.
        </p>
        <p>
          InfraSketch takes this further by using AI to generate diagrams from natural language.
          Instead of dragging shapes onto a canvas, you describe what you want to build, and
          the AI creates the architecture for you.
        </p>
      </div>

      {/* Features Grid */}
      <div className="tool-section">
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

      {/* Use Cases */}
      <div className="tool-section tool-section-alt">
        <h2>Use Cases</h2>
        <div className="use-cases-grid">
          {USE_CASES.map((useCase, index) => (
            <div key={index} className="use-case-card">
              <div className="use-case-icon">{useCase.icon}</div>
              <h3>{useCase.title}</h3>
              <p>{useCase.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How It Works */}
      <div className="tool-section">
        <h2>How It Works</h2>
        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">1</div>
            <h3 className="step-title">Describe Your System</h3>
            <p className="step-description">
              Write a natural language description like "Design a video streaming platform with CDN, transcoding, and recommendations"
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">AI Generates Diagram</h3>
            <p className="step-description">
              Our AI analyzes your requirements and creates a complete architecture with appropriate components and connections
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Refine Through Chat</h3>
            <p className="step-description">
              Click any component to ask questions or request changes. The AI updates your diagram based on your feedback.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">4</div>
            <h3 className="step-title">Export & Share</h3>
            <p className="step-description">
              Export your diagram as PNG, PDF, or generate a comprehensive design document with implementation details
            </p>
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

      {/* Learn More Section */}
      <div className="tool-section">
        <h2>Learn More About System Design</h2>
        <div className="learn-more-grid">
          <Link to="/blog/complete-guide-system-design" className="learn-more-card">
            <span className="learn-more-icon">📖</span>
            <h3>Complete Guide to System Design</h3>
            <p>Master system design from fundamentals to advanced patterns used by top tech companies.</p>
          </Link>
          <Link to="/blog/system-design-interview-cheat-sheet" className="learn-more-card">
            <span className="learn-more-icon">📋</span>
            <h3>Interview Cheat Sheet</h3>
            <p>Quick reference for system design interviews at Google, Meta, Amazon, and more.</p>
          </Link>
          <Link to="/blog/architecture-diagram-best-practices" className="learn-more-card">
            <span className="learn-more-icon">✏️</span>
            <h3>Diagram Best Practices</h3>
            <p>Learn how to create effective architecture diagrams that communicate clearly.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Ready to Design Your System?</h2>
        <p>Create your first architecture diagram in seconds. No signup required.</p>
        <Link to="/" className="tool-cta-button">
          Start Designing Free
        </Link>
      </div>

      <Footer />
    </div>
  );
}
