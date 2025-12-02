import { Link } from 'react-router-dom';
import '../App.css';

export default function CareersPage() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <Link to="/" className="legal-back-link">&larr; Back to InfraSketch</Link>
        <h1>Careers</h1>
      </div>

      <div className="legal-content">
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
      </div>
    </div>
  );
}
