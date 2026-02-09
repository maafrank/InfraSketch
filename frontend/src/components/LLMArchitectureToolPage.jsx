import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

const FEATURES = [
  {
    icon: "🤖",
    title: "LLM Application Architecture",
    description: "Generate complete architectures for LLM-powered applications including RAG pipelines, chatbots, and AI agents from natural language."
  },
  {
    icon: "🔍",
    title: "RAG System Design",
    description: "Design retrieval-augmented generation systems with document ingestion, embedding pipelines, vector databases, and generation layers."
  },
  {
    icon: "🔗",
    title: "Agent Architectures",
    description: "Diagram multi-agent systems, tool-calling agents, and orchestration workflows with LangGraph, LangChain, or custom frameworks."
  },
  {
    icon: "💬",
    title: "Conversational Refinement",
    description: "Refine your LLM architecture through chat. Add guardrails, caching layers, evaluation pipelines, or cost optimization strategies."
  },
  {
    icon: "📄",
    title: "Auto Design Documents",
    description: "Generate detailed documentation covering system components, data flows, API contracts, prompt strategies, and scaling considerations."
  },
  {
    icon: "📤",
    title: "Export and Share",
    description: "Export LLM architecture diagrams as PNG, PDF, or Markdown for design reviews, technical documentation, or presentations."
  }
];

const USE_CASES = [
  {
    title: "RAG Applications",
    description: "Design document Q&A systems, knowledge bases, and semantic search applications with vector databases and retrieval pipelines.",
    icon: "📚"
  },
  {
    title: "Production Chatbots",
    description: "Architect chatbot systems with conversation management, tool integration, guardrails, and observability for production deployment.",
    icon: "💬"
  },
  {
    title: "AI Agent Systems",
    description: "Design agentic AI architectures with multi-agent orchestration, tool calling, state management, and human-in-the-loop patterns.",
    icon: "🧠"
  },
  {
    title: "LLM Infrastructure",
    description: "Plan LLM serving infrastructure with prompt caching, model routing, cost management, and evaluation pipelines.",
    icon: "🏗️"
  }
];

const FAQS = [
  {
    question: "How do I design a RAG system architecture?",
    answer: "Describe your RAG use case in InfraSketch (e.g., 'Design a RAG system for customer support with document ingestion, vector search, and response generation'). The AI generates a complete architecture with ingestion pipelines, chunking, embedding generation, vector database, retrieval, re-ranking, and generation components. Refine through chat to add specific components like metadata filtering or hybrid search."
  },
  {
    question: "What is the best tool for LLM application architecture?",
    answer: "InfraSketch is purpose-built for designing AI system architectures. Unlike general diagramming tools, InfraSketch understands LLM-specific components like vector databases, embedding models, prompt chains, and agent orchestration. It generates architectures from natural language and lets you refine through conversation."
  },
  {
    question: "Can I diagram multi-agent AI systems?",
    answer: "Yes. InfraSketch can generate architectures for multi-agent systems including supervisor patterns, peer-to-peer agent collaboration, hierarchical agent teams, and tool-calling workflows. Describe your agent system, and the AI creates a diagram showing agent interactions, shared state, tool integrations, and communication patterns."
  },
  {
    question: "How do I design a production chatbot architecture?",
    answer: "Describe your chatbot requirements (e.g., 'Design a customer service chatbot with conversation memory, tool calling for order lookups, content moderation, and analytics'). InfraSketch generates the full architecture including the LLM layer, conversation management, tool integration, guardrails, and monitoring. Then refine through chat to handle edge cases."
  },
  {
    question: "Does InfraSketch support LangGraph and LangChain architectures?",
    answer: "Yes. InfraSketch is itself built on LangGraph, so it deeply understands graph-based LLM orchestration patterns. You can design LangGraph state machines, LangChain pipelines, and custom orchestration architectures. The AI generates appropriate components for nodes, edges, conditional routing, and tool execution."
  }
];

export default function LLMArchitectureToolPage() {
  const pageSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "SoftwareApplication",
        "name": "InfraSketch LLM Architecture Tool",
        "description": "AI-powered tool for designing LLM application architectures. Generate RAG system diagrams, chatbot architectures, and agent system designs from natural language.",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Web Browser",
        "url": "https://infrasketch.net/tools/llm-architecture-tool",
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
            "name": "LLM Architecture Tool",
            "item": "https://infrasketch.net/tools/llm-architecture-tool"
          }
        ]
      }
    ]
  };

  return (
    <div className="landing-page tool-landing-page">
      <Helmet>
        <title>LLM Architecture Tool | Design RAG, Chatbot & Agent Systems | InfraSketch</title>
        <meta name="description" content="Design LLM application architectures with AI. Generate RAG system diagrams, chatbot architectures, and multi-agent system designs from plain English descriptions." />
        <meta name="keywords" content="LLM architecture tool, RAG system design, chatbot architecture diagram, agent system design, LangGraph architecture, LLM application design, vector database architecture, AI agent diagram" />
        <link rel="canonical" href="https://infrasketch.net/tools/llm-architecture-tool" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="LLM Architecture Tool | Design RAG, Chatbot & Agent Systems" />
        <meta property="og:description" content="Design LLM application architectures with AI. Generate RAG, chatbot, and agent system diagrams from plain English." />
        <meta property="og:url" content="https://infrasketch.net/tools/llm-architecture-tool" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="LLM Architecture Tool | Design RAG, Chatbot & Agent Systems" />
        <meta name="twitter:description" content="Design LLM application architectures with AI. Generate RAG, chatbot, and agent system diagrams." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <script type="application/ld+json">
          {JSON.stringify(pageSchema)}
        </script>
      </Helmet>

      <Header />

      {/* Hero Section */}
      <div className="tool-hero-section">
        <h1 className="tool-hero-title">
          LLM Architecture Design Tool
        </h1>
        <p className="tool-hero-subtitle">
          Design RAG systems, chatbots, and AI agent architectures in seconds.
          Describe your LLM application, get a production-ready architecture diagram.
        </p>
        <Link to="/" className="tool-cta-button">
          Try It Free
        </Link>
      </div>

      {/* What Is Section */}
      <div className="tool-section">
        <h2>Design LLM Applications with AI</h2>
        <p>
          Building production LLM applications involves more than just calling an API.
          You need retrieval pipelines, vector databases, prompt management, guardrails,
          evaluation systems, and cost controls, all connected in the right architecture.
        </p>
        <p>
          InfraSketch generates complete LLM application architectures from natural language.
          Whether you are building a RAG system, a production chatbot, or a multi-agent
          workflow, describe what you need and get an architecture diagram in seconds.
          InfraSketch is itself built on LangGraph and Claude, so it understands LLM
          architecture patterns from first-hand experience.
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
            <h3 className="step-title">Describe Your LLM Application</h3>
            <p className="step-description">
              Write a description like "Design a customer support chatbot with RAG over our knowledge base, tool calling for order lookups, and conversation memory"
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">2</div>
            <h3 className="step-title">AI Generates Architecture</h3>
            <p className="step-description">
              The AI creates a complete architecture showing your LLM orchestration, data pipelines, vector stores, tools, and infrastructure
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">3</div>
            <h3 className="step-title">Refine Through Chat</h3>
            <p className="step-description">
              Ask the AI to add guardrails, caching, evaluation pipelines, or scale specific components. Your diagram updates in real-time.
            </p>
          </div>
          <div className="step-card">
            <div className="step-number">4</div>
            <h3 className="step-title">Export Documentation</h3>
            <p className="step-description">
              Generate comprehensive design docs with component details, data flows, API contracts, and deployment strategies
            </p>
          </div>
        </div>
      </div>

      {/* Example Prompts */}
      <div className="tool-section tool-section-alt">
        <h2>Example LLM Architecture Prompts</h2>
        <div className="when-to-use-grid">
          <div className="when-to-use-card">
            <h3>RAG Knowledge Base</h3>
            <p>"Design a RAG system for internal documentation search with PDF ingestion, semantic chunking, Pinecone vector store, and a chat interface with citation tracking"</p>
          </div>
          <div className="when-to-use-card">
            <h3>AI Agent Platform</h3>
            <p>"Design a multi-agent system where a supervisor agent delegates to specialist agents for code generation, research, and data analysis, with shared memory and tool access"</p>
          </div>
          <div className="when-to-use-card">
            <h3>Customer Support Bot</h3>
            <p>"Design a production chatbot for e-commerce support with order lookup tools, return processing, FAQ retrieval, human escalation, and conversation analytics"</p>
          </div>
          <div className="when-to-use-card">
            <h3>Content Generation Pipeline</h3>
            <p>"Design an AI content pipeline with topic research, outline generation, draft writing, fact-checking, SEO optimization, and human review workflow"</p>
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
        <h2>Learn More About LLM Architecture</h2>
        <div className="learn-more-grid">
          <Link to="/blog/llm-system-design-architecture" className="learn-more-card">
            <span className="learn-more-icon">📖</span>
            <h3>LLM System Design Guide</h3>
            <p>Complete guide to building production LLM applications with RAG, agents, and scaling patterns.</p>
          </Link>
          <Link to="/blog/agentic-ai-system-architecture" className="learn-more-card">
            <span className="learn-more-icon">🧠</span>
            <h3>Agentic AI Architecture</h3>
            <p>Design multi-agent systems with supervisor patterns, tool calling, and state management.</p>
          </Link>
          <Link to="/blog/vector-database-system-design" className="learn-more-card">
            <span className="learn-more-icon">🔍</span>
            <h3>Vector Database Design</h3>
            <p>Understand vector database architecture, indexing strategies, and integration patterns.</p>
          </Link>
        </div>
      </div>

      {/* CTA Section */}
      <div className="tool-section tool-cta-section">
        <h2>Ready to Design Your LLM Application?</h2>
        <p>Create your first LLM architecture diagram in seconds. No signup required.</p>
        <Link to="/" className="tool-cta-button">
          Start Designing Free
        </Link>
      </div>

      <Footer />
    </div>
  );
}
