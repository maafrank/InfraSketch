# InfraSketch Conversion Strategy: The Deal Framing

_Drafted: 2026-04-27. Re-evaluate after each conversion-analysis run._

## The signal we're acting on

From [conversion-analysis-2026-04-27.md](conversion-analysis-2026-04-27.md):

- **2 of 3 paying customers redeemed `FREE100` before paying.** Of the only "real" converter in the cohort (the one with deep usage history), the promo was part of the path.
- 0% hit the free credit wall (HTTP 402) before paying — so the upgrade trigger is **interest and perceived value**, not pain.
- Median real converter sampled the product deeply (48 diagrams, 4 different models, 30 design-doc actions) before paying $4.99 for Pro.

N is tiny (effectively 1 real converter), so this is a hypothesis we're acting on, not a proven law. We re-evaluate weekly via [scripts/lambda_conversion_report.py](../scripts/lambda_conversion_report.py).

## The hypothesis

People convert when they feel they're getting a **deal**, not when they hit a wall. `FREE100` (100 free credits, currently unlimited redemptions) is doing the work of:

1. Giving runway to discover the product's value (10x the default 10-credit free tier).
2. Triggering the "I have to use this before I lose it" loss-aversion instinct.
3. Making the user feel like an insider who has a code others don't.

`Pro` at $4.99 is already cheap. The promo isn't a discount on price — it's a **gift of headroom that converts curiosity into commitment**.

## The strategy

Treat `FREE100` (or a rotating named variant) as the **headline acquisition offer**. The deal isn't hidden in the pricing page; it's the lead.

Three principles:

1. **Visibility** — the offer is the first thing people see on the landing page, in videos, in articles. Not buried in pricing.
2. **Specificity** — "100 free credits" beats "free trial." A specific number triggers anchoring and the math ("how many diagrams is that?").
3. **Manufactured scarcity** — bound the codes by time, count, or audience. "First 500 builders," "ends Dec 31," "for /r/devops readers only." Unlimited free credits with no urgency is a free product, not a deal.

## Tactical actions

### P0 — Product changes (need user approval before merge)

**1. Landing page hero: lead with the deal.**

Add a visible promo banner above or inside the hero CTA: _"Get 100 free credits with code `FREE100` — enough for 20 system designs. No credit card."_ One-click copy button on the code. Files: [frontend/src/components/LandingPage.jsx](../frontend/src/components/LandingPage.jsx).

**2. Pre-fill the promo code in the upgrade modal.**

When the upgrade flow opens (whether from /pricing, a 402 error, or a feature gate), pre-populate the promo input with the active code and show "FREE100 applied — +100 credits." Currently the field is empty and easy to miss. Files: [frontend/src/components/PricingPage.jsx](../frontend/src/components/PricingPage.jsx) lines 320-349.

**3. Auto-apply the promo on signup if a referral code is present.**

If the user lands with `?promo=FREE100` (link from a video, article, social post), capture it during signup and redeem automatically after Clerk's `user.created` webhook fires. Files: [backend/app/api/routes_billing.py](../backend/app/api/routes_billing.py), [frontend/src/components/LandingPage.jsx](../frontend/src/components/LandingPage.jsx).

**4. Add scarcity to FREE100.**

Currently `FREE100` is `max_uses=None, expires_at=None`. Set `max_uses=500` and `expires_at=2026-07-31`. When 80% of redemptions are used, swap to a successor code (`BUILDER100`, etc.) and update the campaign. Files: [backend/app/billing/promo_codes.py](../backend/app/billing/promo_codes.py).

### P1 — Marketing copy and assets

**One code: `FREE100`.** Multiple channel-specific codes look great for attribution but the current promo system enforces one-redemption-per-code-per-user, not one-redemption-per-user. A savvy reader of multiple channels could stack BUILDER100 + DEMO100 + SHOWHN100 + FRIENDS100 + FREE100 for 500 free credits. Until [backend/app/billing/promo_codes.py](../backend/app/billing/promo_codes.py) and the `redeemed_promo_codes` storage logic are extended to enforce a global one-promo-per-user cap, push a single code.

`FREE100` is what the existing converters used. Keep boasting about it everywhere — it's the brand offer, not a campaign.

**5. Video script template.**

Every video opens with a 5-second hook + closes with the deal: _"Code `FREE100` gets you 100 free credits — that's 20 system designs free. Link in the description."_ Stick a lower-third with the code visible for the whole video. Pin the code in the YouTube description and the first comment.

**6. Article boilerplate.**

End every blog post with a one-paragraph callout box: _"Try InfraSketch free with code `FREE100` — 100 credits, no card required."_ Apply to existing posts in [frontend/public/blog/posts/](../frontend/public/blog/posts/).

**7. Social posts.**

Every product tweet, LinkedIn post, or Mastodon post that mentions InfraSketch closes with `FREE100`. Pin a profile tweet with the offer.

**8. Email signups.**

The welcome email auto-sent on Clerk `user.created` (via `infrasketch-subscribers`) already exists. Add a section: _"Founder gift: code `FREE100` for 100 credits — already added to your account."_ If you auto-redeem (action #3 above), frame it as a gift the user already has.

**9. Channel attribution without multi-codes.**

To know which channel is actually converting, lean on URL params instead of multiple codes:
- Use `utm_source` / `utm_campaign` on every link (`?utm_source=youtube&utm_campaign=ep03&promo=FREE100`).
- Capture utm params on landing in [frontend/src/components/LandingPage.jsx](../frontend/src/components/LandingPage.jsx), persist them on the user record, and emit them in the `user.created` log event.
- The conversion report already filters by user — extend it to break out the cohort by `utm_source` once that field exists.

This gives you per-channel attribution without giving any single user 500 free credits.

### P2 — Measurement and iteration

**10. Track redemption volume in the conversion report.**

`redeemed_promo_codes` is already aggregated in [scripts/analyze_conversions.py](../scripts/analyze_conversions.py). Each weekly Lambda run shows what % of converters used `FREE100`. Watch this stay above 50% — if it drops, the deal is getting stale.

**11. Add a "FREE100 redeemed → paid" funnel metric.**

Compute: `(users who redeemed FREE100) → (users who later paid)`. This single ratio tells you whether the promo is bringing real intent or just tire-kickers. If 5% of redeemers eventually pay, the deal is doing its job.

**12. Measure time-from-redemption-to-paid.**

If users typically pay within 7 days of redeeming, the promo is the ignition. If they pay 60+ days later, the promo is just brand awareness. Different conclusions, different next moves.

**13. Channel attribution via UTMs (see action #9).**

Once landing-page UTM capture lands, extend the conversion report to slice the cohort by `utm_source`. That gives you per-channel ROI without needing per-channel codes.

## Open questions before shipping

- **Cannibalization risk**: do users who would have paid full price now redeem a promo and pay later (or never)? With Pro at $4.99 and starter at $1, the absolute revenue at risk is small — but for someone on Enterprise this matters more.
- **Quality of redemption**: are promo redeemers more likely to churn? Once we have 10+ paying customers we can compare lifetime value of promo vs non-promo conversions.
- **Brand positioning**: is "deal-driven" the right vibe for a developer tool, or does it cheapen the product? Stripe doesn't run promos. Linear doesn't. But Vercel's free tier IS the promo. We're closer to Vercel.

## What's NOT in this plan

- Discounting Pro/Enterprise plan prices. The deal is bonus credits, not cheaper subscription.
- Free trials of paid features. Design doc generation is a once-only preview today; that's working — keep it.
- Bombarding users in-app with upgrade modals. The current "interest, not pain" pattern says don't push too hard.

## Next checkpoint

After [scripts/lambda_conversion_report.py](../scripts/lambda_conversion_report.py) runs for 4 weeks (or after we hit 10 paying customers — whichever is first):

- Has the % of paying customers who used `FREE100` stayed >50%?
- Has time-to-convert dropped now that the deal is the lead?
- Is the FREE100-redeemed → paid conversion rate trending up, flat, or down?

If yes to the first two, the strategy is working. If the redeemed→paid rate is dropping, the deal is bringing in tire-kickers — tighten scarcity (lower `max_uses`, shorter expiry) before adding more channels.

Only consider a second code (`LIFER` for annual prepay, `FOUNDERS` for early supporters, etc.) once `promo_codes.py` and the `redeemed_promo_codes` logic enforce a global one-promo-per-user cap. Otherwise stacking is back on the menu.
