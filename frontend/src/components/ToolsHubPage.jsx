import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

const TOOLS = [
  {
    path: '/tools/system-design-tool',
    icon: '🏗️',
    name: 'System Design Tool',
    description:
      'Describe your architecture in plain English and get instant diagrams. Perfect for system design interviews, documentation, and rapid prototyping.',
  },
  {
    path: '/tools/ai-diagram-generator',
    icon: '🤖',
    name: 'AI Diagram Generator',
    description:
      'Generate architecture diagrams from natural language descriptions. Powered by Claude AI. Free to try, no signup required.',
  },
  {
    path: '/tools/architecture-diagram-tool',
    icon: '🏛️',
    name: 'Architecture Diagram Tool',
    description:
      'Create AWS, GCP, Azure, and microservices architecture diagrams. Generate professional diagrams from plain English descriptions.',
  },
  {
    path: '/tools/design-doc-generator',
    icon: '📄',
    name: 'Design Doc Generator',
    description:
      'Auto-generate comprehensive design documents from architecture diagrams. The only AI tool that creates both diagrams and documentation. Export to PDF or Markdown.',
  },
  {
    path: '/tools/ml-system-design-tool',
    icon: '🧠',
    name: 'ML System Design Tool',
    description:
      'Design ML pipelines, recommendation systems, and MLOps infrastructure with AI. Generate machine learning architecture diagrams from plain English.',
  },
  {
    path: '/tools/llm-architecture-tool',
    icon: '💬',
    name: 'LLM Architecture Tool',
    description:
      'Design RAG systems, chatbot architectures, and multi-agent systems. Generate LLM application diagrams from plain English descriptions.',
  },
];

export default function ToolsHubPage() {
  const pageSchema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebPage',
        name: 'AI System Design Tools',
        description:
          'Free AI-powered tools for system design, architecture diagrams, and design documentation. Browse all InfraSketch tools.',
        url: 'https://infrasketch.net/tools',
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          {
            '@type': 'ListItem',
            position: 1,
            name: 'Home',
            item: 'https://infrasketch.net',
          },
          {
            '@type': 'ListItem',
            position: 2,
            name: 'Tools',
            item: 'https://infrasketch.net/tools',
          },
        ],
      },
      {
        '@type': 'ItemList',
        itemListElement: TOOLS.map((tool, index) => ({
          '@type': 'ListItem',
          position: index + 1,
          url: `https://infrasketch.net${tool.path}`,
          name: tool.name,
        })),
      },
    ],
  };

  return (
    <div className="landing-page tool-landing-page compare-page">
      <Helmet>
        <title>AI System Design Tools | Free Architecture Diagram Tools | InfraSketch</title>
        <meta
          name="description"
          content="Free AI-powered tools for system design, architecture diagrams, and design documentation. Browse all InfraSketch tools for engineers, architects, and ML teams."
        />
        <meta
          name="keywords"
          content="AI system design tools, architecture diagram tools, AI diagram generator, design doc generator, ML system design, LLM architecture tools"
        />
        <link rel="canonical" href="https://infrasketch.net/tools" />

        <meta property="og:type" content="website" />
        <meta
          property="og:title"
          content="AI System Design Tools | Free Architecture Diagram Tools | InfraSketch"
        />
        <meta
          property="og:description"
          content="Free AI-powered tools for system design, architecture diagrams, and design documentation."
        />
        <meta property="og:url" content="https://infrasketch.net/tools" />
        <meta
          property="og:image"
          content="https://infrasketch.net/full-app-with-design-doc.png"
        />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="AI System Design Tools | InfraSketch" />
        <meta
          name="twitter:description"
          content="Free AI-powered tools for system design and architecture diagrams."
        />
        <meta
          name="twitter:image"
          content="https://infrasketch.net/full-app-with-design-doc.png"
        />

        <script type="application/ld+json">{JSON.stringify(pageSchema)}</script>
      </Helmet>

      <Header />

      <div className="tool-hero-section">
        <h1 className="tool-hero-title">AI System Design Tools</h1>
        <p className="tool-hero-subtitle">
          Free AI-powered tools for architecture diagrams, system design, and
          design documentation. Pick a tool below to get started.
        </p>
      </div>

      <div className="tool-section">
        <h2>Browse All Tools</h2>
        <div className="learn-more-grid">
          {TOOLS.map((tool) => (
            <Link key={tool.path} to={tool.path} className="learn-more-card">
              <span className="learn-more-icon">{tool.icon}</span>
              <h3>{tool.name}</h3>
              <p>{tool.description}</p>
            </Link>
          ))}
        </div>
      </div>

      <div className="tool-section tool-section-alt">
        <h2>Why InfraSketch?</h2>
        <div className="why-choose-grid">
          <div className="why-choose-card">
            <h3>Plain English Input</h3>
            <p>
              Skip the drag-and-drop. Describe what you want to build in natural
              language and get a complete diagram in seconds.
            </p>
          </div>
          <div className="why-choose-card">
            <h3>Conversational Refinement</h3>
            <p>
              Chat with the AI to iterate. Ask for changes like "add caching" or
              "what if we 10x scale?" and watch your design evolve.
            </p>
          </div>
          <div className="why-choose-card">
            <h3>Auto-Generated Docs</h3>
            <p>
              Every diagram can become a full design document with component
              details, data flows, and implementation notes.
            </p>
          </div>
          <div className="why-choose-card">
            <h3>Free to Start</h3>
            <p>
              10 free credits per month, no credit card required. Upgrade only
              when you need more.
            </p>
          </div>
        </div>
      </div>

      <div className="tool-section tool-cta-section">
        <h2>Ready to Design Your System?</h2>
        <p>Start with any tool above, or jump straight in.</p>
        <Link to="/" className="tool-cta-button">
          Try InfraSketch Free
        </Link>
      </div>

      <Footer />
    </div>
  );
}
