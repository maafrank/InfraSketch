import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './BlogListPage.css';

export default function BlogPostPage() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Load post metadata
    fetch('/blog/posts/index.json')
      .then(res => res.json())
      .then(data => {
        const foundPost = data.posts.find(p => p.slug === slug);
        if (foundPost) {
          setPost(foundPost);
          // Load post content
          return fetch(`/blog/posts/${slug}.md`);
        } else {
          throw new Error('Post not found');
        }
      })
      .then(res => {
        if (!res.ok) throw new Error('Failed to load post content');
        return res.text();
      })
      .then(markdown => {
        setContent(markdown);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load blog post:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [slug]);

  if (loading) {
    return (
      <div className="blog-post-page">
        <div className="blog-post-header">
          <Link to="/blog" className="blog-back-link">&larr; Back to Blog</Link>
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="blog-post-page">
        <div className="blog-post-header">
          <Link to="/blog" className="blog-back-link">&larr; Back to Blog</Link>
          <h1>Post Not Found</h1>
          <p>The blog post you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  // Generate Article schema for structured data
  const articleSchema = post ? {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": post.title,
    "description": post.description,
    "datePublished": post.date,
    "dateModified": post.date,
    "author": {
      "@type": "Organization",
      "name": "InfraSketch",
      "url": "https://infrasketch.net"
    },
    "publisher": {
      "@type": "Organization",
      "name": "InfraSketch",
      "logo": {
        "@type": "ImageObject",
        "url": "https://infrasketch.net/InfraSketchLogoTransparent_01.png"
      }
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": `https://infrasketch.net/blog/${slug}`
    },
    "image": "https://infrasketch.net/og-image.png"
  } : null;

  return (
    <div className="blog-post-page">
      {post && (
        <Helmet>
          <title>{post.title} | InfraSketch Blog</title>
          <meta name="description" content={post.description} />
          <link rel="canonical" href={`https://infrasketch.net/blog/${slug}`} />

          {/* Open Graph */}
          <meta property="og:type" content="article" />
          <meta property="og:title" content={post.title} />
          <meta property="og:description" content={post.description} />
          <meta property="og:url" content={`https://infrasketch.net/blog/${slug}`} />
          <meta property="og:image" content="https://infrasketch.net/og-image.png" />
          <meta property="og:site_name" content="InfraSketch" />
          <meta property="article:published_time" content={post.date} />
          <meta property="article:author" content="InfraSketch Team" />

          {/* Twitter Card */}
          <meta name="twitter:card" content="summary_large_image" />
          <meta name="twitter:title" content={post.title} />
          <meta name="twitter:description" content={post.description} />
          <meta name="twitter:image" content="https://infrasketch.net/og-image.png" />

          {/* Article Schema */}
          <script type="application/ld+json">
            {JSON.stringify(articleSchema)}
          </script>
        </Helmet>
      )}

      <div className="blog-post-header">
        <Link to="/blog" className="blog-back-link">&larr; Back to Blog</Link>
        <h1>{post.title}</h1>
        <div className="blog-post-header-meta">
          {new Date(post.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} • {post.author}{post.readingTime && ` • ${post.readingTime}`}
        </div>
      </div>

      <div className="blog-post-body">
        <div className="blog-post-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              img: ({ src, alt }) => {
                // Check if this is a YouTube thumbnail - embed video instead
                const youtubeMatch = src?.match(/img\.youtube\.com\/vi\/([^/]+)/);
                if (youtubeMatch) {
                  const videoId = youtubeMatch[1];
                  return (
                    <div className="youtube-embed">
                      <iframe
                        src={`https://www.youtube-nocookie.com/embed/${videoId}`}
                        title={alt || "YouTube video"}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                  );
                }
                return <img src={src} alt={alt} />;
              }
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>

      <footer className="blog-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">Agent-powered system architecture design</p>
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
