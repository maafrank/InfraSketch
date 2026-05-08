import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import Header from './shared/Header';
import Footer from './shared/Footer';

export default function NotFoundPage() {
  return (
    <div>
      <Helmet>
        <title>Page Not Found | InfraSketch</title>
        <meta name="robots" content="noindex,nofollow" />
      </Helmet>
      <Header />
      <main style={{ padding: '4rem 2rem', textAlign: 'center', minHeight: '60vh' }}>
        <h1>404 - Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <p><Link to="/">Return home</Link></p>
      </main>
      <Footer />
    </div>
  );
}
