import { Helmet } from 'react-helmet-async';
import Header from './shared/Header';
import Footer from './shared/Footer';
import '../App.css';

export default function CareersPage() {
  return (
    <div className="legal-page">
      <Helmet>
        <title>Careers at InfraSketch | Join Our Team</title>
        <meta name="description" content="Join InfraSketch and help build the future of agent-powered system design. View open positions and learn about our culture." />
        <link rel="canonical" href="https://infrasketch.net/careers" />

        <meta property="og:type" content="website" />
        <meta property="og:title" content="Careers at InfraSketch" />
        <meta property="og:description" content="Join InfraSketch and help build the future of agent-powered system design." />
        <meta property="og:url" content="https://infrasketch.net/careers" />
        <meta property="og:image" content="https://infrasketch.net/full-app-with-design-doc.png" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Careers at InfraSketch" />
        <meta name="twitter:description" content="Join InfraSketch and help build the future of agent-powered system design." />
        <meta name="twitter:image" content="https://infrasketch.net/full-app-with-design-doc.png" />
      </Helmet>

      <Header />

      <main className="legal-content">
        <h1>Careers</h1>
        <section className="careers-hero">
          <h2>Join Our Team</h2>
          <p>
            We're building the future of system architecture design with AI.
            InfraSketch helps engineers visualize and document their ideas faster
            than ever before.
          </p>
        </section>

        <section className="careers-status">
          <div className="careers-notice">
            <h3>No Open Positions</h3>
            <p>
              We're not currently hiring, but we're always interested in connecting
              with talented people. Check back soon for future opportunities.
            </p>
          </div>
        </section>

        <section>
          <h2>Why InfraSketch?</h2>
          <ul>
            <li>Work on cutting-edge AI technology</li>
            <li>Build tools that engineers actually love using</li>
            <li>Remote-friendly culture</li>
            <li>Early-stage startup with room to grow</li>
          </ul>
        </section>

        <section>
          <h2>Stay Connected</h2>
          <p>
            Want to be notified when positions open up? Drop us a line at{' '}
            <a href="mailto:contact@infrasketch.net">contact@infrasketch.net</a>{' '}
            and we'll keep you in the loop.
          </p>
        </section>
      </main>

      <Footer />
    </div>
  );
}
