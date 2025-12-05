import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
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
        <div className="blog-header">
          <Link to="/" className="blog-back-link">&larr; Back to InfraSketch</Link>
          <h1>Blog</h1>
        </div>
        <div className="blog-content">
          <p>Loading posts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="blog-page">
      <Helmet>
        <title>System Design Blog | InfraSketch</title>
        <meta name="description" content="Learn about system design, software architecture patterns, and AI-powered development tools. Tutorials, guides, and best practices for engineers." />
        <link rel="canonical" href="https://infrasketch.net/blog" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content="System Design Blog | InfraSketch" />
        <meta property="og:description" content="Learn about system design, software architecture patterns, and AI-powered development tools." />
        <meta property="og:url" content="https://infrasketch.net/blog" />
        <meta property="og:image" content="https://infrasketch.net/og-image.png" />
        <meta property="og:site_name" content="InfraSketch" />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="System Design Blog | InfraSketch" />
        <meta name="twitter:description" content="Learn about system design, software architecture patterns, and AI-powered development tools." />
        <meta name="twitter:image" content="https://infrasketch.net/og-image.png" />
      </Helmet>

      <div className="blog-header">
        <Link to="/" className="blog-back-link">&larr; Back to InfraSketch</Link>
        <h1>Blog</h1>
        <p className="blog-subtitle">Insights on system design, architecture, and AI-powered development tools</p>
      </div>

      <div className="blog-content">
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

      <footer className="blog-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">AI-powered system architecture design</p>
          </div>
          <div className="footer-links">
            <Link to="/about">About</Link>
            <Link to="/blog">Blog</Link>
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
