import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

const FEATURES = [
  {
    icon: "🧠",
    title: "ML Pipeline Generation",
    description: "Describe your ML system and get a complete architecture diagram with data ingestion, feature engineering, training, and serving components."
  },
  {
    icon: "🔄",
    title: "End-to-End Architecture",
    description: "Generate diagrams covering the full ML lifecycle: data collection, preprocessing, model training, deployment, and monitoring."
  },
  {
    icon: "💬",
    title: "Refine Through Chat",
    description: "Ask the AI to add model registries, feature stores, A/B testing, or monitoring. Iterate on your ML architecture through conversation."
  },
  {
    icon: "📄",
    title: "Auto Design Documents",
    description: "Generate comprehensive design docs covering data pipelines, model specifications, infrastructure requirements, and scaling strategies."
  },
  {
    icon: "⚡",
    title: "Production Patterns",
    description: "Get architectures that follow production ML best practices: batch vs real-time serving, model versioning, drift detection, and rollback."
  },
  {
    icon: "📤",
    title: "Export and Share",
    description: "Export your ML architecture diagrams as PNG, PDF, or Markdown. Share with your ML engineering team or include in design reviews."
  }
];

const USE_CASES = [
  {
    title: "ML Pipeline Architecture",
    description: "Design end-to-end ML pipelines with data ingestion, feature engineering, model training, and serving infrastructure.",
    icon: "🔬"
  },
  {
    title: "Recommendation Systems",
    description: "Architect recommendation engines with candidate generation, ranking models, feature stores, and real-time serving.",
    icon: "🎯"
  },
  {
    title: "MLOps Infrastructure",
    description: "Plan your MLOps stack with model registries, CI/CD pipelines, monitoring, and automated retraining workflows.",
    icon: "🏗️"
  },
  {
    title: "Real-Time ML Serving",
    description: "Design low-latency inference systems with model optimization, caching, load balancing, and GPU scheduling.",
    icon: "⚡"
  }
];

const FAQS = [
  {
    question: "Can InfraSketch generate ML pipeline architecture diagrams?",
    answer: "Yes. Describe your ML system in plain English, and InfraSketch generates a complete architecture diagram showing data pipelines, feature stores, training infrastructure, model serving, and monitoring components. You can then refine the design through chat."
  },
  {
    question: "What AI/ML components does InfraSketch support?",
    answer: "InfraSketch supports all standard ML infrastructure components including data lakes, feature stores, training clusters, model registries, inference servers, vector databases, message queues, monitoring systems, and more. The AI understands ML-specific patterns and best practices."
  },
  {
    question: "How do I design a recommendation system architecture?",
    answer: "Describe your recommendation use case (e.g., 'Design a movie recommendation system with collaborative filtering and content-based features'). InfraSketch generates the architecture with candidate generation, ranking pipelines, feature stores, and A/B testing infrastructure. Refine through chat to add specific components."
  },
  {
    question: "Can I diagram RAG and LLM architectures?",
    answer: "Yes. InfraSketch can generate architectures for RAG systems, LLM applications, chatbots, and agentic AI systems. Describe your use case, and the AI creates diagrams showing embedding pipelines, vector databases, retrieval components, and generation layers."
  },
  {
    question: "Is InfraSketch useful for ML system design interviews?",
    answer: "Absolutely. ML system design is an increasingly common interview topic at top tech companies. Use InfraSketch to practice designing recommendation engines, search ranking systems, fraud detection pipelines, and other ML systems. The auto-generated design docs help you think through all aspects of the system."
  }
];

export default function MLSystemDesignToolPage() {
  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "name": "InfraSketch ML System Design Tool",
        "description": "AI-powered tool for designing machine learning system architectures. Generate ML pipeline diagrams, recommendation system architectures, and MLOps infrastructure from natural language.",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net/tools/ml-system-design-tool",
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
            "name": "ML System Design Tool",
            "item": "https://infrasketch.net/tools/ml-system-design-tool"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page">
      <Helmet>
        <title>ML System Design Tool | AI Architecture Diagrams for Machine Learning | InfraSketch</title>
        <meta name="description" content="Design machine learning system architectures with AI. Generate ML pipeline diagrams, recommendation systems, and MLOps infrastructure from plain English descriptions." />
        <meta name="keywords" content="ML system design tool, machine learning architecture diagram, ML pipeline diagram, recommendation system design, MLOps architecture, AI architecture diagram, feature store diagram, model serving architecture" />
        <link rel="canonical" href="https://infrasketch.net/tools/ml-system-design-tool" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="ML System Design Tool | AI Architecture Diagrams for Machine Learning" />
        <meta property="og:description" content="Design machine learning system architectures with AI. Generate ML pipeline diagrams from plain English." />
        <meta property="og:url" content="https://infrasketch.net/tools/ml-system-design-tool" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="ML System Design Tool | AI Architecture Diagrams for ML" />
        <meta name="twitter:description" content="Design machine learning system architectures with AI. Generate ML pipeline diagrams from plain English." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          ML System Design Tool
        </h1>
        <p className="tool-hero-subtitle">
          Describe your machine learning system in plain English.
          Get a complete architecture diagram with data pipelines, model serving, and monitoring.
        </p>
        <Link to="/" className="tool-cta-button">
          Try It Free
        </Link>
      </div>

      {/* What Is Section */}
      <div className="tool-section">
        <h2>Design ML Architectures with AI</h2>
        <p>
          Machine learning systems are complex. They involve data pipelines, feature engineering,
          model training, serving infrastructure, and monitoring, all working together.
          Designing these systems from scratch on a blank canvas is slow and error-prone.
        </p>
        <p>
          InfraSketch generates complete ML architecture diagrams from natural language descriptions.
          Describe what you want to build, and the AI creates a production-ready architecture
          following ML engineering best practices. Then refine through conversation to add
          feature stores, model registries, A/B testing, or any other component you need.
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
            <h3 className="step-title">Describe Your ML System</h3>
            <p className="step-description">
              Write a description like "Design a recommendation engine with collaborative filtering, a feature store, real-time serving, and A/B testing"
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">AI Generates Architecture</h3>
            <p className="step-description">
              The AI creates a complete ML system architecture with appropriate components, data flows, and infrastructure patterns
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Refine Through Chat</h3>
            <p className="step-description">
              Ask the AI to add monitoring, change the serving pattern, or scale specific components. The diagram updates in real-time.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">4</div>
            <h3 className="step-title">Export Documentation</h3>
            <p className="step-description">
              Generate a comprehensive design document covering data pipelines, model specs, infrastructure, and scaling strategies
            </p>
          </div>
        </div>
      </div>

      {/* Example Prompts */}
      <div className="tool-section tool-section-alt">
        <h2>Example ML Architecture Prompts</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>Recommendation Engine</h3>
            <p>"Design a recommendation system for an e-commerce platform with collaborative filtering, content-based features, a feature store, real-time serving layer, and A/B testing infrastructure"</p>
          </div>
          <div className="when-to-use-card">
            <h3>Fraud Detection Pipeline</h3>
            <p>"Design a real-time fraud detection system with streaming data ingestion from Kafka, feature computation, model serving with sub-100ms latency, and an alert system"</p>
          </div>
          <div className="when-to-use-card">
            <h3>Computer Vision Pipeline</h3>
            <p>"Design an image classification system with data labeling workflow, distributed training on GPUs, model registry, and REST API serving with auto-scaling"</p>
          </div>
          <div className="when-to-use-card">
            <h3>NLP Processing Platform</h3>
            <p>"Design a text analytics platform with document ingestion, embedding generation, semantic search with a vector database, and a summarization API"</p>
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
        <h2>Learn More About ML System Design</h2>
        <div className="learn-more-grid">
          <Link to="/blog/ml-system-design-patterns" className="learn-more-card">
            <span className="learn-more-icon">📖</span>
            <h3>ML System Design Patterns</h3>
            <p>Complete guide to machine learning system design patterns for production systems.</p>
          </Link>
          <Link to="/blog/real-world-ai-system-architecture" className="learn-more-card">
            <span className="learn-more-icon">🏢</span>
            <h3>Real-World AI Architectures</h3>
            <p>Case studies from Netflix, Uber, Spotify, and more showing production ML systems.</p>
          </Link>
          <Link to="/blog/llm-system-design-architecture" className="learn-more-card">
            <span className="learn-more-icon">🤖</span>
            <h3>LLM System Design</h3>
            <p>Design RAG systems, chatbots, and agentic AI applications with production architectures.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Ready to Design Your ML System?</h2>
        <p>Create your first ML architecture diagram in seconds. No signup required.</p>
        <Link to="/" className="tool-cta-button">
          Start Designing Free
        </Link>
      </div>

      <Footer />
    </div>
  );
}
