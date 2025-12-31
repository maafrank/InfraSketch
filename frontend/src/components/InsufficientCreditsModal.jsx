import { useState } from 'react';
import { redeemPromoCode } from '../api/client';
import './InsufficientCreditsModal.css';

/**
 * InsufficientCreditsModal - Modal shown when user runs out of credits.
 * Offers upgrade options and promo code redemption.
 */
export default function InsufficientCreditsModal({
  isOpen,
  onClose,
  required,
  available,
  onUpgrade,
  onCreditsUpdated,
}) {
  const [promoCode, setPromoCode] = useState('');
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoError, setPromoError] = useState(null);
  const [promoSuccess, setPromoSuccess] = useState(null);

  if (!isOpen) return null;

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
      if (onCreditsUpdated) {
        onCreditsUpdated();
      }
      // Close modal after short delay if they now have enough credits
      if (result.new_balance >= required) {
        setTimeout(() => {
          onClose();
        }, 1500);
      }
    } catch (err) {
      setPromoError(err.response?.data?.detail || 'Invalid promo code');
    } finally {
      setPromoLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="insufficient-credits-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          &times;
        </button>

        <div className="modal-icon">⚡</div>

        <h2>Out of Credits</h2>

        <p className="modal-description">
          This action requires <strong>{required} credits</strong>,
          but you only have <strong>{available} credits</strong> available.
        </p>

        <div className="modal-actions">
          <button className="action-button primary" onClick={onUpgrade}>
            Upgrade Plan
          </button>
        </div>

        <div className="promo-section">
          <p className="promo-label">Have a promo code?</p>
          <form onSubmit={handlePromoSubmit} className="promo-form">
            <input
              type="text"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
              placeholder="Enter code"
              className="promo-input"
              disabled={promoLoading}
            />
            <button
              type="submit"
              className="promo-submit"
              disabled={promoLoading || !promoCode.trim()}
            >
              {promoLoading ? '...' : 'Apply'}
            </button>
          </form>
          {promoError && <p className="promo-error">{promoError}</p>}
          {promoSuccess && <p className="promo-success">{promoSuccess}</p>}
        </div>
      </div>
    </div>
  );
}
