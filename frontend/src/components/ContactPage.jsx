import { useState } from 'react';
import { Link } from 'react-router-dom';
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
