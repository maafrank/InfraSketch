import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

export default function AboutPage() {
  return (
    <div className="legal-page about-page">
      <Helmet>
        <title>About InfraSketch | Agent-Powered System Design Tool</title>
        <meta name="description" content="Learn how InfraSketch transforms plain English descriptions into professional system architecture diagrams using Sketch, our AI design agent. Built with Claude AI, React, and AWS." />
        <link rel="canonical" href="https://infrasketch.net/about" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="About InfraSketch | Agent-Powered System Design Tool" />
        <meta property="og:description" content="Learn how InfraSketch transforms plain English descriptions into professional system architecture diagrams using Sketch, our AI design agent." />
        <meta property="og:url" content="https://infrasketch.net/about" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="About InfraSketch | Agent-Powered System Design Tool" />
        <meta name="twitter:description" content="Learn how InfraSketch transforms plain English descriptions into professional system architecture diagrams using Sketch, our AI design agent." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />
      </Helmet>

      <Header />

      <main className="legal-content">
        <h1>About InfraSketch</h1>

        <section>
          <h2>What is InfraSketch?</h2>
          <p>
            InfraSketch is an agent-powered tool that transforms plain English descriptions
            into professional system architecture diagrams. Whether you're a software
            engineer designing a new microservices platform, a startup founder sketching
            your MVP, or a student learning about distributed systems, InfraSketch helps
            you visualize and document your ideas in seconds.
          </p>
        </section>

        <section>
          <h2>How It Works</h2>
          <div className="about-steps">
            <div className="about-step">
              <div className="about-step-number">1</div>
              <div className="about-step-content">
                <h3>Describe Your System</h3>
                <p>
                  Write a natural language description of the system you want to build.
                  For example: "A video streaming platform with CDN, transcoding pipeline,
                  and recommendation engine."
                </p>
              </div>
            </div>
            <div className="about-step">
              <div className="about-step-number">2</div>
              <div className="about-step-content">
                <h3>Sketch Generates Your Diagram</h3>
                <p>
                  Sketch analyzes your description and creates a complete architecture
                  diagram with appropriate components, connections, and labels.
                </p>
              </div>
            </div>
            <div className="about-step">
              <div className="about-step-number">3</div>
              <div className="about-step-content">
                <h3>Refine Through Conversation</h3>
                <p>
                  Click any component to ask questions or request changes. The AI
                  understands context and can modify your diagram based on your feedback.
                </p>
              </div>
            </div>
            <div className="about-step">
              <div className="about-step-number">4</div>
              <div className="about-step-content">
                <h3>Generate Documentation</h3>
                <p>
                  With one click, generate comprehensive technical documentation including
                  component details, data flows, and implementation recommendations.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h2>Our Technology</h2>
          <p>InfraSketch is built with modern, reliable technology:</p>
          <ul>
            <li>
              <strong>Claude AI by Anthropic</strong> - Powers our intelligent diagram
              generation and conversational interface
            </li>
            <li>
              <strong>React</strong> - Fast, responsive user interface
            </li>
            <li>
              <strong>React Flow</strong> - Interactive diagram visualization
            </li>
            <li>
              <strong>AWS</strong> - Secure, scalable cloud infrastructure
            </li>
            <li>
              <strong>LangGraph</strong> - Orchestrates AI agent workflows
            </li>
          </ul>
        </section>

        <section>
          <h2>Our Mission</h2>
          <p>
            We believe that great architecture starts with clear communication. Too often,
            valuable engineering time is spent drawing diagrams instead of building systems.
            InfraSketch bridges the gap between ideas and implementation by making it easy
            to create, share, and iterate on system designs.
          </p>
          <p>
            Our goal is to democratize system design - making professional-quality
            architecture diagrams accessible to everyone, from seasoned architects to
            those just starting their engineering journey.
          </p>
        </section>

        <section>
          <h2>Get in Touch</h2>
          <p>
            Have questions, feedback, or feature requests? We'd love to hear from you.
          </p>
          <p>
            <a href="mailto:contact@infrasketch.net">contact@infrasketch.net</a>
          </p>
        </section>

        <section className="about-cta">
          <h2>Ready to Start Designing?</h2>
          <p>
            Create your first architecture diagram in seconds.
          </p>
          <Link to="/" className="about-cta-button">
            Try InfraSketch Free
          </Link>
        </section>
      </main>

      <Footer />
    </div>
  );
}
