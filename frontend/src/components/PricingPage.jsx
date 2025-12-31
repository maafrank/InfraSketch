import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, SignedIn, SignedOut, SignInButton } from '@clerk/clerk-react';
import { CheckoutButton } from '@clerk/clerk-react/experimental';
import { redeemPromoCode, getUserCredits, setClerkTokenGetter } from '../api/client';
import './PricingPage.css';

/**
 * PricingPage - Displays subscription plans with Clerk Billing checkout.
 * Users can subscribe to Pro or Enterprise plans via Clerk's checkout flow.
 */

// Clerk plan IDs from dashboard
const CLERK_PLAN_IDS = {
  pro: 'cplan_37cOR2Mjs1jWOjaJfUGTX0U1Jf4',
  enterprise: 'cplan_37cOpDf5Cm7GGUl2K8lUarQf7Bp',
};

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: 'forever',
    credits: 25,
    features: [
      '25 credits per month',
      'AI-powered diagram generation',
      'Chat-based modifications',
      'Design document export',
      'All node types',
    ],
    cta: 'Current Plan',
  },
  {
    id: 'pro',
    clerkPlanId: CLERK_PLAN_IDS.pro,
    name: 'Pro',
    price: '$19',
    period: '/month',
    credits: 500,
    features: [
      '500 credits per month',
      'Everything in Free',
      'Priority generation queue',
      'Claude Sonnet 4.5 access',
      'Email support',
    ],
    cta: 'Upgrade to Pro',
    highlighted: true,
  },
  {
    id: 'enterprise',
    clerkPlanId: CLERK_PLAN_IDS.enterprise,
    name: 'Enterprise',
    price: '$49',
    period: '/month',
    credits: 2000,
    features: [
      '2000 credits per month',
      'Everything in Pro',
      'Team collaboration (coming soon)',
      'API access (coming soon)',
      'Priority support',
    ],
    cta: 'Upgrade to Enterprise',
  },
];

export default function PricingPage() {
  const navigate = useNavigate();
  const { isSignedIn, getToken } = useAuth();
  const [promoCode, setPromoCode] = useState('');
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoError, setPromoError] = useState(null);
  const [promoSuccess, setPromoSuccess] = useState(null);
  const [currentPlan, setCurrentPlan] = useState('free');
  const [loadingPlan, setLoadingPlan] = useState(true);

  // Set up Clerk token getter for API calls
  useEffect(() => {
    setClerkTokenGetter(getToken);
  }, [getToken]);

  // Fetch user's current plan
  const fetchCurrentPlan = useCallback(async () => {
    if (!isSignedIn) {
      setCurrentPlan('free');
      setLoadingPlan(false);
      return;
    }

    try {
      const credits = await getUserCredits();
      setCurrentPlan(credits.plan || 'free');
    } catch (error) {
      console.error('Failed to fetch current plan:', error);
      setCurrentPlan('free');
    } finally {
      setLoadingPlan(false);
    }
  }, [isSignedIn]);

  useEffect(() => {
    fetchCurrentPlan();
  }, [fetchCurrentPlan]);

  const handlePromoSubmit = async (e) => {
    e.preventDefault();
    if (!promoCode.trim()) return;

    setPromoLoading(true);
    setPromoError(null);
    setPromoSuccess(null);

    try {
      const result = await redeemPromoCode(promoCode.trim());
      setPromoSuccess(`${result.credits_granted} credits added! New balance: ${result.new_balance}`);
      setPromoCode('');
    } catch (err) {
      setPromoError(err.response?.data?.detail || 'Invalid promo code');
    } finally {
      setPromoLoading(false);
    }
  };

  const handleSubscriptionComplete = () => {
    // Refresh the plan after successful subscription
    fetchCurrentPlan();
    // Navigate to settings to see updated credits
    navigate('/settings');
  };

  const isCurrentPlan = (planId) => {
    return currentPlan === planId;
  };

  const canUpgrade = (planId) => {
    const planOrder = { free: 0, pro: 1, enterprise: 2 };
    return planOrder[planId] > planOrder[currentPlan];
  };

  return (
    <div className="pricing-page">
      <header className="pricing-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back to App
        </button>
        <h1>Choose Your Plan</h1>
        <p className="pricing-subtitle">
          Get more credits to create diagrams and design documents
        </p>
      </header>

      <main className="pricing-content">
        <div className="pricing-grid">
          {PLANS.map((plan) => {
            const isCurrent = isCurrentPlan(plan.id);
            const canUpgradeToPlan = canUpgrade(plan.id);

            return (
              <div
                key={plan.id}
                className={`pricing-card ${plan.highlighted ? 'highlighted' : ''} ${isCurrent ? 'current' : ''}`}
              >
                {plan.highlighted && <div className="popular-badge">Most Popular</div>}
                <h2 className="plan-name">{plan.name}</h2>
                <div className="plan-price">
                  <span className="price">{plan.price}</span>
                  <span className="period">{plan.period}</span>
                </div>
                <div className="plan-credits">
                  <span className="credits-count">{plan.credits}</span>
                  <span className="credits-label">credits/month</span>
                </div>
                <ul className="plan-features">
                  {plan.features.map((feature, index) => (
                    <li key={index}>{feature}</li>
                  ))}
                </ul>

                {/* Render appropriate button based on plan and auth state */}
                {loadingPlan ? (
                  <button className="plan-cta" disabled>
                    Loading...
                  </button>
                ) : isCurrent ? (
                  <button className="plan-cta current" disabled>
                    Current Plan
                  </button>
                ) : plan.id === 'free' ? (
                  // Free plan - no action needed if user is on a paid plan
                  <button className="plan-cta" disabled>
                    {currentPlan !== 'free' ? 'Downgrade via Settings' : 'Sign in to start'}
                  </button>
                ) : (
                  // Paid plans - use Clerk CheckoutButton
                  <>
                    <SignedIn>
                      {canUpgradeToPlan ? (
                        <CheckoutButton
                          planId={plan.clerkPlanId}
                          planPeriod="month"
                          onSubscriptionComplete={handleSubscriptionComplete}
                        >
                          <button className="plan-cta">
                            {plan.cta}
                          </button>
                        </CheckoutButton>
                      ) : (
                        <button className="plan-cta" disabled>
                          {currentPlan === 'enterprise' ? 'You have the best plan' : 'Contact for downgrade'}
                        </button>
                      )}
                    </SignedIn>
                    <SignedOut>
                      <SignInButton mode="modal">
                        <button className="plan-cta">
                          Sign in to {plan.cta}
                        </button>
                      </SignInButton>
                    </SignedOut>
                  </>
                )}
              </div>
            );
          })}
        </div>

        <section className="promo-section">
          <h2>Have a promo code?</h2>
          <p>Enter your code below to get free credits</p>
          <form onSubmit={handlePromoSubmit} className="promo-form">
            <input
              type="text"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
              placeholder="Enter promo code"
              className="promo-input"
              disabled={promoLoading || !isSignedIn}
            />
            <button
              type="submit"
              className="promo-submit"
              disabled={promoLoading || !promoCode.trim() || !isSignedIn}
            >
              {promoLoading ? 'Applying...' : 'Apply Code'}
            </button>
          </form>
          {!isSignedIn && (
            <div className="promo-signin-note">
              <SignInButton mode="modal">
                <button className="promo-signin-button">Sign in to redeem promo codes</button>
              </SignInButton>
            </div>
          )}
          {promoError && <p className="promo-error">{promoError}</p>}
          {promoSuccess && <p className="promo-success">{promoSuccess}</p>}
        </section>

        <section className="credit-costs-section">
          <h2>Credit Usage</h2>
          <p>Here's how credits are consumed:</p>
          <div className="credit-costs-grid">
            <div className="credit-cost-item">
              <span className="cost-action">Diagram Generation</span>
              <span className="cost-amount">5-15 credits</span>
              <span className="cost-note">5 (Haiku) / 15 (Sonnet)</span>
            </div>
            <div className="credit-cost-item">
              <span className="cost-action">Chat Message</span>
              <span className="cost-amount">1-3 credits</span>
              <span className="cost-note">1 (Haiku) / 3 (Sonnet)</span>
            </div>
            <div className="credit-cost-item">
              <span className="cost-action">Design Doc Generation</span>
              <span className="cost-amount">10 credits</span>
              <span className="cost-note">Per document</span>
            </div>
            <div className="credit-cost-item">
              <span className="cost-action">Export (PDF/Markdown)</span>
              <span className="cost-amount">2 credits</span>
              <span className="cost-note">Per export</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
