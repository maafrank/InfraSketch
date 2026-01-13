import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './BlogListPage.css';

// Get related posts based on category and tags
function getRelatedPosts(currentPost, allPosts, maxPosts = 3) {
  if (!currentPost || !allPosts) return [];

  const otherPosts = allPosts.filter(p => p.slug !== currentPost.slug);

  // Score each post based on relevance
  const scoredPosts = otherPosts.map(post => {
    let score = 0;

    // Same category = high relevance
    if (post.category && currentPost.category && post.category === currentPost.category) {
      score += 10;
    }

    // Shared tags = medium relevance
    if (post.tags && currentPost.tags) {
      const sharedTags = post.tags.filter(tag => currentPost.tags.includes(tag));
      score += sharedTags.length * 3;
    }

    // Recency bonus (newer posts slightly preferred)
    const postDate = new Date(post.date);
    const daysSincePost = (Date.now() - postDate.getTime()) / (1000 * 60 * 60 * 24);
    if (daysSincePost < 30) score += 2;
    else if (daysSincePost < 90) score += 1;

    return { ...post, score };
  });

  // Sort by score (descending), then by date (most recent first)
  scoredPosts.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return new Date(b.date) - new Date(a.date);
  });

  return scoredPosts.slice(0, maxPosts);
}

export default function BlogPostPage() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [allPosts, setAllPosts] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Load post metadata
    fetch('/blog/posts/index.json')
      .then(res => res.json())
      .then(data => {
        setAllPosts(data.posts);
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

  // Get related posts
  const relatedPosts = getRelatedPosts(post, allPosts);

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
        "url": "https://infrasketch.net/InfraSketchLogoTransparent_02.png"
      }
    },
    "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": `https://infrasketch.net/blog/${slug}`
    },
    "image": "https://infrasketch.net/og-image.png"
  } : null;

  // Generate BreadcrumbList schema for better SERP appearance
  const breadcrumbSchema = post ? {
    "@context": "https://schema.org",
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
        "name": "Blog",
        "item": "https://infrasketch.net/blog"
      },
      {
        "@type": "ListItem",
        "position": 3,
        "name": post.title,
        "item": `https://infrasketch.net/blog/${slug}`
      }
    ]
  } : null;

  return (
    <div className="blog-post-page">
      {post && (
        <Helmet>
          <title>{post.title} | InfraSketch Blog</title>
          <meta name="description" content={post.description} />
          {post.tags && post.tags.length > 0 && (
            <meta name="keywords" content={post.tags.join(', ')} />
          )}
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

          {/* Breadcrumb Schema */}
          <script type="application/ld+json">
            {JSON.stringify(breadcrumbSchema)}
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
                        src={`https://www.youtube.com/embed/${videoId}`}
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

      {/* Related Posts Section */}
      {relatedPosts.length > 0 && (
        <div className="related-posts-section">
          <div className="related-posts-container">
            <h2 className="related-posts-title">Related Articles</h2>
            <div className="related-posts-grid">
              {relatedPosts.map(relatedPost => (
                <Link
                  key={relatedPost.slug}
                  to={`/blog/${relatedPost.slug}`}
                  className="related-post-card"
                >
                  <span className="related-post-category">{relatedPost.category || 'Article'}</span>
                  <h3 className="related-post-title">{relatedPost.title}</h3>
                  <p className="related-post-description">{relatedPost.description}</p>
                  <div className="related-post-meta">
                    {new Date(relatedPost.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    {relatedPost.readingTime && ` • ${relatedPost.readingTime}`}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

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
