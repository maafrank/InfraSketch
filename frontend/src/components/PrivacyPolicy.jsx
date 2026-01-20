import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

export default function PrivacyPolicy() {
  return (
    <div className="legal-page">
      <Helmet>
        <title>Privacy Policy | InfraSketch</title>
        <meta name="description" content="InfraSketch privacy policy. Learn how we collect, use, and protect your data when using our agent-powered system design tool." />
        <link rel="canonical" href="https://infrasketch.net/privacy" />
        <meta name="robots" content="noindex, follow" />
      </Helmet>

      <Header />

      <main className="legal-content">
        <h1>Privacy Policy</h1>
        <p className="legal-updated">Last updated: December 2, 2025</p>
        <section>
          <h2>Introduction</h2>
          <p>
            InfraSketch ("we," "our," or "us") is committed to protecting your privacy.
            This Privacy Policy explains how we collect, use, and safeguard your information
            when you use our agent-powered system architecture design tool.
          </p>
        </section>

        <section>
          <h2>Information We Collect</h2>

          <h3>Account Information</h3>
          <p>
            When you create an account, we collect your email address and basic profile
            information through our authentication provider, Clerk. This information is
            used to identify you and provide access to your saved designs.
          </p>

          <h3>Design Data</h3>
          <p>
            We store the system architecture diagrams you create, including:
          </p>
          <ul>
            <li>Diagram nodes and connections</li>
            <li>Design documents you generate</li>
            <li>Chat conversations about your designs</li>
            <li>Session metadata (creation time, last modified)</li>
          </ul>

          <h3>Usage Data</h3>
          <p>
            We automatically collect certain information when you use InfraSketch, including:
          </p>
          <ul>
            <li>IP address (anonymized for logging purposes)</li>
            <li>Browser type and version</li>
            <li>Pages visited and features used</li>
            <li>Time and date of visits</li>
          </ul>
        </section>

        <section>
          <h2>How We Use Your Information</h2>
          <p>We use the information we collect to:</p>
          <ul>
            <li>Provide, maintain, and improve InfraSketch</li>
            <li>Save and retrieve your diagram designs</li>
            <li>Generate agent-powered architecture suggestions</li>
            <li>Respond to your inquiries and support requests</li>
            <li>Monitor and analyze usage patterns to improve our service</li>
            <li>Protect against unauthorized access and abuse</li>
          </ul>
        </section>

        <section>
          <h2>Data Storage and Security</h2>
          <p>
            Your data is stored securely on Amazon Web Services (AWS) infrastructure
            in the United States. We implement industry-standard security measures
            including encryption in transit and at rest.
          </p>
          <p>
            <strong>Session Data Retention:</strong> Design sessions are retained for
            up to 1 year. You can delete your sessions at any time from the session
            history sidebar, or export them for permanent storage.
          </p>
        </section>

        <section>
          <h2>Third-Party Services</h2>
          <p>We use the following third-party services to operate InfraSketch:</p>
          <ul>
            <li>
              <strong>Clerk</strong> - Authentication and user management.
              <a href="https://clerk.com/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
            </li>
            <li>
              <strong>Anthropic (Claude AI)</strong> - Powers our Sketch agent for diagram generation.
              <a href="https://www.anthropic.com/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
            </li>
            <li>
              <strong>Amazon Web Services</strong> - Cloud infrastructure and hosting.
              <a href="https://aws.amazon.com/privacy/" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
            </li>
          </ul>
        </section>

        <section>
          <h2>Your Rights</h2>
          <p>You have the right to:</p>
          <ul>
            <li>Access your personal data</li>
            <li>Request correction of inaccurate data</li>
            <li>Request deletion of your data</li>
            <li>Export your diagrams and designs</li>
            <li>Withdraw consent for data processing</li>
          </ul>
          <p>
            To exercise any of these rights, please contact us at{' '}
            <a href="mailto:contact@infrasketch.net">contact@infrasketch.net</a>.
          </p>
        </section>

        <section>
          <h2>Cookies</h2>
          <p>
            We use essential cookies to maintain your login session and preferences.
            We do not use tracking cookies or share cookie data with third parties
            for advertising purposes.
          </p>
        </section>

        <section>
          <h2>Children's Privacy</h2>
          <p>
            InfraSketch is not intended for children under 13 years of age. We do not
            knowingly collect personal information from children under 13.
          </p>
        </section>

        <section>
          <h2>Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. Any changes will
            be posted on this page with an updated "Last updated" date. We encourage
            you to review this page periodically for any changes.
          </p>
        </section>

        <section>
          <h2>Contact Us</h2>
          <p>
            If you have any questions about this Privacy Policy, please contact us at:
          </p>
          <p>
            <a href="mailto:contact@infrasketch.net">contact@infrasketch.net</a>
          </p>
        </section>
      </main>

      <Footer />
    </div>
  );
}
