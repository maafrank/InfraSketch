import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import './BlogListPage.css';

export default function BlogListPage() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/blog/posts/index.json')
      .then(res => res.json())
      .then(data => {
        setPosts(data.posts);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load blog posts:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="blog-page">
        <Header />
        <div className="blog-header">
          <h1>Blog</h1>
        </div>
        <div className="blog-content">
          <p>Loading posts...</p>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="blog-page">
      <Helmet>
        <title>System Design & AI Architecture Blog | InfraSketch</title>
        <meta name="description" content="Learn about system design, AI/ML architecture patterns, LLM system design, and software engineering best practices. Tutorials, guides, and interview prep for engineers." />
        <meta name="keywords" content="system design blog, AI architecture blog, machine learning system design, LLM system design, RAG architecture, MLOps, software architecture tutorials, AI diagram generation, system design interview prep, distributed systems, cloud architecture, microservices patterns" />
        <link rel="canonical" href="https://infrasketch.net/blog" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content="System Design Blog | InfraSketch" />
        <meta property="og:description" content="Learn about system design, software architecture patterns, and AI-powered development tools." />
        <meta property="og:url" content="https://infrasketch.net/blog" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />
        <meta property="og:site_name" content="InfraSketch" />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="System Design Blog | InfraSketch" />
        <meta name="twitter:description" content="Learn about system design, software architecture patterns, and AI-powered development tools." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />
      </Helmet>

      <Header />

      <div className="blog-header">
        <h1>Blog</h1>
        <p className="blog-subtitle">Insights on system design, architecture, and AI-powered development tools</p>
      </div>

      <div className="blog-content">
        {/* Featured External Content */}
        <section className="featured-section">
          <h2 className="featured-title">Featured Articles & Videos</h2>
          <p className="featured-subtitle">More InfraSketch content across the web</p>
          <div className="featured-cards">
            <a
              href="https://dev.to/matt_frank_usa/6-machine-learning-system-design-patterns-every-engineer-should-know-1a0e"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M7.42 10.05c-.18-.16-.46-.23-.84-.23H6v4.36h.58c.37 0 .65-.08.84-.23.21-.17.32-.44.32-.84v-2.22c0-.4-.11-.68-.32-.84zm3.75-.23h-.78v4.36h.78c.42 0 .72-.1.91-.3.2-.2.3-.5.3-.88v-2c0-.38-.1-.68-.3-.88-.19-.2-.49-.3-.91-.3zM22 7.25v9.5c0 1-.81 1.75-1.75 1.75H3.75C2.75 18.5 2 17.75 2 16.75v-9.5C2 6.25 2.75 5.5 3.75 5.5h16.5c.94 0 1.75.75 1.75 1.75zM8.8 14.18c0 .57-.14 1-.43 1.3-.28.3-.7.45-1.24.45H5.5V8.07h1.63c.54 0 .96.15 1.24.44.3.3.43.73.43 1.3v4.37zm4.7-1.43c0 .62-.16 1.1-.47 1.45-.31.35-.76.53-1.34.53h-1.7V8.07h1.7c.58 0 1.03.18 1.34.53.31.35.47.83.47 1.45v2.7zm5-4.68h-3.5v6.11h1.3v-2.25h2.2V10.6h-2.2V9.37h2.2V8.07z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Dev.to</span>
                <h3 className="featured-card-title">6 Machine Learning System Design Patterns Every Engineer Should Know</h3>
                <p className="featured-card-description">Master the essential ML patterns for production: batch prediction, real-time inference, feature stores, and more.</p>
              </div>
            </a>

            <a
              href="https://dev.to/matt_frank_usa/how-to-design-llm-applications-for-production-a-system-design-guide-2i3h"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M7.42 10.05c-.18-.16-.46-.23-.84-.23H6v4.36h.58c.37 0 .65-.08.84-.23.21-.17.32-.44.32-.84v-2.22c0-.4-.11-.68-.32-.84zm3.75-.23h-.78v4.36h.78c.42 0 .72-.1.91-.3.2-.2.3-.5.3-.88v-2c0-.38-.1-.68-.3-.88-.19-.2-.49-.3-.91-.3zM22 7.25v9.5c0 1-.81 1.75-1.75 1.75H3.75C2.75 18.5 2 17.75 2 16.75v-9.5C2 6.25 2.75 5.5 3.75 5.5h16.5c.94 0 1.75.75 1.75 1.75zM8.8 14.18c0 .57-.14 1-.43 1.3-.28.3-.7.45-1.24.45H5.5V8.07h1.63c.54 0 .96.15 1.24.44.3.3.43.73.43 1.3v4.37zm4.7-1.43c0 .62-.16 1.1-.47 1.45-.31.35-.76.53-1.34.53h-1.7V8.07h1.7c.58 0 1.03.18 1.34.53.31.35.47.83.47 1.45v2.7zm5-4.68h-3.5v6.11h1.3v-2.25h2.2V10.6h-2.2V9.37h2.2V8.07z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Dev.to</span>
                <h3 className="featured-card-title">How to Design LLM Applications for Production</h3>
                <p className="featured-card-description">A system design guide covering RAG pipelines, vector databases, agent architectures, and scaling strategies.</p>
              </div>
            </a>

            <a
              href="https://dev.to/matt_frank_usa/how-netflix-uber-and-google-build-ai-systems-architecture-deep-dive-17g5"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M7.42 10.05c-.18-.16-.46-.23-.84-.23H6v4.36h.58c.37 0 .65-.08.84-.23.21-.17.32-.44.32-.84v-2.22c0-.4-.11-.68-.32-.84zm3.75-.23h-.78v4.36h.78c.42 0 .72-.1.91-.3.2-.2.3-.5.3-.88v-2c0-.38-.1-.68-.3-.88-.19-.2-.49-.3-.91-.3zM22 7.25v9.5c0 1-.81 1.75-1.75 1.75H3.75C2.75 18.5 2 17.75 2 16.75v-9.5C2 6.25 2.75 5.5 3.75 5.5h16.5c.94 0 1.75.75 1.75 1.75zM8.8 14.18c0 .57-.14 1-.43 1.3-.28.3-.7.45-1.24.45H5.5V8.07h1.63c.54 0 .96.15 1.24.44.3.3.43.73.43 1.3v4.37zm4.7-1.43c0 .62-.16 1.1-.47 1.45-.31.35-.76.53-1.34.53h-1.7V8.07h1.7c.58 0 1.03.18 1.34.53.31.35.47.83.47 1.45v2.7zm5-4.68h-3.5v6.11h1.3v-2.25h2.2V10.6h-2.2V9.37h2.2V8.07z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Dev.to</span>
                <h3 className="featured-card-title">How Netflix, Uber, and Google Build AI Systems</h3>
                <p className="featured-card-description">Architecture deep dive into real-world AI systems at top tech companies.</p>
              </div>
            </a>

            <a
              href="https://dev.to/matt_frank_usa/building-multi-agent-ai-systems-architecture-patterns-and-best-practices-5cf"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M7.42 10.05c-.18-.16-.46-.23-.84-.23H6v4.36h.58c.37 0 .65-.08.84-.23.21-.17.32-.44.32-.84v-2.22c0-.4-.11-.68-.32-.84zm3.75-.23h-.78v4.36h.78c.42 0 .72-.1.91-.3.2-.2.3-.5.3-.88v-2c0-.38-.1-.68-.3-.88-.19-.2-.49-.3-.91-.3zM22 7.25v9.5c0 1-.81 1.75-1.75 1.75H3.75C2.75 18.5 2 17.75 2 16.75v-9.5C2 6.25 2.75 5.5 3.75 5.5h16.5c.94 0 1.75.75 1.75 1.75zM8.8 14.18c0 .57-.14 1-.43 1.3-.28.3-.7.45-1.24.45H5.5V8.07h1.63c.54 0 .96.15 1.24.44.3.3.43.73.43 1.3v4.37zm4.7-1.43c0 .62-.16 1.1-.47 1.45-.31.35-.76.53-1.34.53h-1.7V8.07h1.7c.58 0 1.03.18 1.34.53.31.35.47.83.47 1.45v2.7zm5-4.68h-3.5v6.11h1.3v-2.25h2.2V10.6h-2.2V9.37h2.2V8.07z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Dev.to</span>
                <h3 className="featured-card-title">Building Multi-Agent AI Systems: Architecture Patterns</h3>
                <p className="featured-card-description">Design patterns for agentic AI, including supervisor, hierarchical, and peer-to-peer architectures with LangGraph.</p>
              </div>
            </a>

            <a
              href="https://dev.to/matt_frank_usa/vector-databases-explained-architecture-and-system-design-for-ai-apps-41pg"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M7.42 10.05c-.18-.16-.46-.23-.84-.23H6v4.36h.58c.37 0 .65-.08.84-.23.21-.17.32-.44.32-.84v-2.22c0-.4-.11-.68-.32-.84zm3.75-.23h-.78v4.36h.78c.42 0 .72-.1.91-.3.2-.2.3-.5.3-.88v-2c0-.38-.1-.68-.3-.88-.19-.2-.49-.3-.91-.3zM22 7.25v9.5c0 1-.81 1.75-1.75 1.75H3.75C2.75 18.5 2 17.75 2 16.75v-9.5C2 6.25 2.75 5.5 3.75 5.5h16.5c.94 0 1.75.75 1.75 1.75zM8.8 14.18c0 .57-.14 1-.43 1.3-.28.3-.7.45-1.24.45H5.5V8.07h1.63c.54 0 .96.15 1.24.44.3.3.43.73.43 1.3v4.37zm4.7-1.43c0 .62-.16 1.1-.47 1.45-.31.35-.76.53-1.34.53h-1.7V8.07h1.7c.58 0 1.03.18 1.34.53.31.35.47.83.47 1.45v2.7zm5-4.68h-3.5v6.11h1.3v-2.25h2.2V10.6h-2.2V9.37h2.2V8.07z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Dev.to</span>
                <h3 className="featured-card-title">Vector Databases Explained: System Design for AI Apps</h3>
                <p className="featured-card-description">Architecture guide covering embeddings, ANN algorithms, and comparison of Pinecone, Weaviate, Milvus, and pgvector.</p>
              </div>
            </a>

            <a
              href="https://dev.to/matt_frank_usa/design-system-architectures-in-minutes-with-ai-48m8"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M7.42 10.05c-.18-.16-.46-.23-.84-.23H6v4.36h.58c.37 0 .65-.08.84-.23.21-.17.32-.44.32-.84v-2.22c0-.4-.11-.68-.32-.84zm3.75-.23h-.78v4.36h.78c.42 0 .72-.1.91-.3.2-.2.3-.5.3-.88v-2c0-.38-.1-.68-.3-.88-.19-.2-.49-.3-.91-.3zM22 7.25v9.5c0 1-.81 1.75-1.75 1.75H3.75C2.75 18.5 2 17.75 2 16.75v-9.5C2 6.25 2.75 5.5 3.75 5.5h16.5c.94 0 1.75.75 1.75 1.75zM8.8 14.18c0 .57-.14 1-.43 1.3-.28.3-.7.45-1.24.45H5.5V8.07h1.63c.54 0 .96.15 1.24.44.3.3.43.73.43 1.3v4.37zm4.7-1.43c0 .62-.16 1.1-.47 1.45-.31.35-.76.53-1.34.53h-1.7V8.07h1.7c.58 0 1.03.18 1.34.53.31.35.47.83.47 1.45v2.7zm5-4.68h-3.5v6.11h1.3v-2.25h2.2V10.6h-2.2V9.37h2.2V8.07z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Dev.to</span>
                <h3 className="featured-card-title">Design System Architectures in Minutes with AI</h3>
                <p className="featured-card-description">Introduction to InfraSketch and how it transforms architecture design workflows.</p>
              </div>
            </a>

            <a
              href="https://medium.com/@Matthew_Frank/i-built-an-ai-tool-that-generates-system-design-diagrams-from-natural-language-bdd14a5bb777"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M13.54 12a6.8 6.8 0 01-6.77 6.82A6.8 6.8 0 010 12a6.8 6.8 0 016.77-6.82A6.8 6.8 0 0113.54 12zM20.96 12c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42M24 12c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75C23.47 6.25 24 8.83 24 12z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Medium</span>
                <h3 className="featured-card-title">I Built an AI Tool That Generates System Design Diagrams from Natural Language</h3>
                <p className="featured-card-description">The story behind InfraSketch and how it transforms architecture design with AI.</p>
              </div>
            </a>

            <a
              href="https://medium.com/aiguys/how-an-ai-tool-helped-me-get-promoted-to-senior-engineer-a28fd5ce95bc"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M13.54 12a6.8 6.8 0 01-6.77 6.82A6.8 6.8 0 010 12a6.8 6.8 0 016.77-6.82A6.8 6.8 0 0113.54 12zM20.96 12c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42M24 12c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75C23.47 6.25 24 8.83 24 12z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">Medium</span>
                <h3 className="featured-card-title">How an AI Tool Helped Me Get Promoted to Senior Engineer</h3>
                <p className="featured-card-description">A personal story about leveraging AI tools to accelerate career growth.</p>
              </div>
            </a>

            <a
              href="https://www.youtube.com/watch?v=4SnRbwlL2VU"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon featured-card-icon-youtube">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">YouTube</span>
                <h3 className="featured-card-title">InfraSketch Demo: System Design in 3 Minutes</h3>
                <p className="featured-card-description">Watch a quick demo of generating architecture diagrams from natural language.</p>
              </div>
            </a>

            <a
              href="https://quickref.me/blog/bridging-the-gap-between-concept-and-code-a-review-of-infrasketch/"
              target="_blank"
              rel="noopener noreferrer"
              className="featured-card"
            >
              <div className="featured-card-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                  <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zm-2-7H8v-2h8v2zm0 4H8v-2h8v2zm-3-8V3.5L18.5 9H13z"/>
                </svg>
              </div>
              <div className="featured-card-content">
                <span className="featured-card-platform">QuickRef.me</span>
                <h3 className="featured-card-title">Bridging the Gap Between Concept and Code: A Review of InfraSketch</h3>
                <p className="featured-card-description">An independent review exploring how InfraSketch bridges vibe coding and production-ready system design.</p>
              </div>
            </a>
          </div>
        </section>

        <h2 className="featured-title">All Posts</h2>
        <div className="blog-posts-list">
          {posts.map(post => (
            <article key={post.slug} className="blog-post-card">
              <Link to={`/blog/${post.slug}`} className="blog-post-link">
                <h2 className="blog-post-title">{post.title}</h2>
                <p className="blog-post-description">{post.description}</p>
                <div className="blog-post-meta">
                  <span className="blog-post-date">{new Date(post.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                  <span className="blog-post-author">by {post.author}</span>
                </div>
              </Link>
            </article>
          ))}
        </div>
      </div>

      <Footer />
    </div>
  );
}
