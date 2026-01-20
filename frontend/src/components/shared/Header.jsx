import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';

export default function Header() {
  return (
    <header className="site-header">
      <div className="header-container">
        <Link to="/" className="header-logo">
          <img
            src="/InfraSketchLogoTransparent_03_256.png"
            alt="InfraSketch Logo"
            className="header-logo-img"
          />
          <span className="header-logo-text">InfraSketch</span>
        </Link>
        <div className="header-auth">
          <SignedOut>
            <SignInButton mode="modal">
              <button className="header-signin-btn">Sign In</button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: { width: 32, height: 32 }
                }
              }}
            />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
