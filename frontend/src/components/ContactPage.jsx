import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import '../App.css';

export default function ContactPage() {
  const [copied, setCopied] = useState(false);
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

        <meta name="twitter:card" content="summary" />
        <meta name="twitter:title" content="Contact Us | InfraSketch" />
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
