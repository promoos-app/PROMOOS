export function PrivacyPolicy() {
  return (
    <div className="fade-up max-w-[900px] mx-auto py-10 px-4 text-[#E4E4E7] leading-relaxed" data-testid="privacy-page">
      <h1 className="font-display font-bold text-4xl mb-2">Privacy Policy</h1>
      <p className="text-xs text-[#71717A] mb-8">Effective February 2026 · PromoOS, a division of Glorified Technology Solution (GTS).</p>
      <Sec title="Data we collect">
        Account information (name, email, password hash), workspace configuration (brand kit, coupons, campaigns), customer identifiers you upload (email or opaque tokens), and product telemetry (redemption events, impressions, referrals).
      </Sec>
      <Sec title="How we use it">
        Solely to deliver the PromoOS service — authentication, workspace isolation, coupon generation, AI copy/image drafting, delivery over email/SMS/WhatsApp, analytics dashboards, and export reports.
      </Sec>
      <Sec title="Third-party sub-processors">
        Emergent LLM (OpenAI, Anthropic, Google) for AI generations · Resend for transactional email · Twilio for SMS + WhatsApp · MongoDB Atlas for storage. Each honors its own privacy commitments.
      </Sec>
      <Sec title="Data retention">
        Redemption + audit records: 24 months. Coupon and workspace configuration: for the lifetime of the account. Soft-deleted accounts retained for 30 days, then purged.
      </Sec>
      <Sec title="Your rights">
        Owners can export or delete their workspace at any time from Settings. Platform administrators respond to data-subject requests within 30 days at privacy@promoos.com.
      </Sec>
      <Sec title="Security">
        Passwords are bcrypt-hashed. Webhook secrets are encrypted at rest with Fernet (AES-128-CBC + HMAC). JWTs are signed with a rotating secret. All requests are served over TLS.
      </Sec>
      <Sec title="Cookies">
        We set a single httpOnly auth cookie (`access_token`). No third-party trackers, no advertising cookies.
      </Sec>
      <Sec title="Contact">
        Glorified Technology Solution (GTS) · privacy@promoos.com.
      </Sec>
    </div>
  );
}

export function TermsOfUse() {
  return (
    <div className="fade-up max-w-[900px] mx-auto py-10 px-4 text-[#E4E4E7] leading-relaxed" data-testid="terms-page">
      <h1 className="font-display font-bold text-4xl mb-2">Terms of Use</h1>
      <p className="text-xs text-[#71717A] mb-8">Effective February 2026 · PromoOS, a division of Glorified Technology Solution (GTS).</p>
      <Sec title="1. Acceptance">
        By accessing PromoOS you agree to these Terms. If you do not agree, discontinue use.
      </Sec>
      <Sec title="2. Your workspace, your responsibility">
        You are responsible for the accuracy of coupons, offers, terms, and audience data you configure. You must comply with all applicable consumer-protection, anti-spam, and telecom laws (including CAN-SPAM, GDPR, CCPA, TCPA) when sending messages through PromoOS.
      </Sec>
      <Sec title="3. Acceptable use">
        No unlawful, deceptive, or misleading promotions. No sending to recipients who have not opted in. No unauthorized access, scraping, or reverse engineering. No use as a spam relay.
      </Sec>
      <Sec title="4. AI outputs">
        AI-generated copy and images are drafts. You are responsible for reviewing and approving every campaign before it is published to customers.
      </Sec>
      <Sec title="5. Fees & billing">
        Free tier limits and paid plan pricing are shown in-app. All fees are non-refundable except where required by law.
      </Sec>
      <Sec title="6. Termination">
        We may suspend or terminate access for material breach. You may cancel at any time; data is retained for 30 days then purged.
      </Sec>
      <Sec title="7. Warranty & liability">
        The service is provided "as is". To the fullest extent permitted by law, GTS's aggregate liability shall not exceed the fees paid in the twelve months preceding a claim.
      </Sec>
      <Sec title="8. Governing law">
        These Terms are governed by the laws of the jurisdiction where GTS is headquartered.
      </Sec>
      <Sec title="9. Contact">
        legal@promoos.com · Glorified Technology Solution (GTS).
      </Sec>
    </div>
  );
}

function Sec({ title, children }) {
  return (
    <section className="mb-6">
      <h2 className="font-display font-bold text-lg mb-2 text-white">{title}</h2>
      <p className="text-sm text-[#A1A1AA]">{children}</p>
    </section>
  );
}
