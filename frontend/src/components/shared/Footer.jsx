import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-content">
        <div className="footer-brand">
          <Link to="/" className="footer-logo">InfraSketch</Link>
          <p className="footer-tagline">AI-powered system design</p>
        </div>
        <div className="footer-columns">
          <div className="footer-column">
            <h4>Products</h4>
            <Link to="/">Design Tool</Link>
            <Link to="/tools/design-doc-generator">Design Docs</Link>
          </div>
          <div className="footer-column">
            <h4>Resources</h4>
            <Link to="/blog">Blog</Link>
            <Link to="/compare">Compare Tools</Link>
          </div>
          <div className="footer-column">
            <h4>Company</h4>
            <Link to="/about">About</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="/careers">Careers</Link>
            <Link to="/contact">Contact</Link>
          </div>
          <div className="footer-column">
            <h4>Legal</h4>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2026 InfraSketch. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
