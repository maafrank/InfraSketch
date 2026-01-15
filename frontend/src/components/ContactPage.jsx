import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import '../App.css';

const CALENDLY_URL = 'https://calendly.com/mattfrank_ai?hide_gdpr_banner=1&background_color=1a1a2e&text_color=e0e0e0&primary_color=00ff88';

export default function ContactPage() {
  const [copied, setCopied] = useState(false);
  const [widgetFailed, setWidgetFailed] = useState(false);

  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://assets.calendly.com/assets/external/widget.js';
    script.async = true;
    document.body.appendChild(script);

    // Detect widget failure after timeout (Calendly sometimes returns X-Frame-Options: DENY)
    const failureTimer = setTimeout(() => {
      const widgetIframe = document.querySelector('.calendly-inline-widget iframe');
      if (!widgetIframe) {
        setWidgetFailed(true);
      }
    }, 5000);

    return () => {
      clearTimeout(failureTimer);
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  const openCalendlyPopup = () => {
    if (window.Calendly) {
      window.Calendly.initPopupWidget({ url: CALENDLY_URL });
    } else {
      // Fallback: open in new tab
      window.open(CALENDLY_URL, '_blank');
    }
  };
  const email = 'contact@infrasketch.net';

  const handleCopyEmail = async () => {
    try {
      await navigator.clipboard.writeText(email);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy email:', err);
    }
  };

  return (
    <div className="legal-page">
      <Helmet>
        <title>Contact Us | InfraSketch</title>
        <meta name="description" content="Get in touch with the InfraSketch team. We'd love to hear your questions, feedback, or feature requests." />
        <link rel="canonical" href="https://infrasketch.net/contact" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="Contact Us | InfraSketch" />
        <meta property="og:description" content="Get in touch with the InfraSketch team. We'd love to hear your questions, feedback, or feature requests." />
        <meta property="og:url" content="https://infrasketch.net/contact" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Contact Us | InfraSketch" />
        <meta name="twitter:description" content="Get in touch with the InfraSketch team." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />
      </Helmet>

      <div className="legal-header">
        <Link to="/" className="legal-back-link">&larr; Back to InfraSketch</Link>
        <h1>Contact Us</h1>
      </div>

      <div className="legal-content">
        <section className="contact-hero">
          <p>
            Have questions, feedback, or just want to say hello? We'd love to hear from you.
          </p>
        </section>

        <section className="contact-info">
          <div className="contact-card">
            <h2>Email</h2>
            <p>The best way to reach us is by email:</p>
            <button onClick={handleCopyEmail} className="contact-email-link">
              {copied ? 'Copied!' : email}
            </button>
          </div>
        </section>

        <section className="contact-info">
          <div className="contact-card calendly-card">
            <h2>Schedule a Call</h2>
            <p>Want to discuss your project or have a detailed conversation? Book a time that works for you:</p>
            {widgetFailed ? (
              <div className="calendly-fallback">
                <p style={{ marginBottom: '1rem', color: '#888' }}>
                  The scheduling widget could not load. Click below to open in a popup:
                </p>
                <button onClick={openCalendlyPopup} className="calendly-fallback-button">
                  Open Scheduler
                </button>
              </div>
            ) : (
              <div
                className="calendly-inline-widget"
                data-url={CALENDLY_URL}
                style={{ minWidth: '320px', height: '700px' }}
              />
            )}
          </div>
        </section>

        <section>
          <h2>What to Include</h2>
          <p>To help us respond quickly, please include:</p>
          <ul>
            <li><strong>Bug reports:</strong> Steps to reproduce, browser/device info, screenshots if helpful</li>
            <li><strong>Feature requests:</strong> Describe your use case and what you're trying to accomplish</li>
            <li><strong>General questions:</strong> As much context as possible</li>
          </ul>
        </section>

        <section>
          <h2>Response Time</h2>
          <p>
            We're a small team and typically respond within 1-2 business days.
            Thanks for your patience!
          </p>
        </section>
      </div>
    </div>
  );
}
