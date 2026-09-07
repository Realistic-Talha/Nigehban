export default function TermsPage() {
  return (
    <div className="page-shell max-w-2xl space-y-6 py-12 sm:py-16">
      <div>
        <p className="page-eyebrow">Legal</p>
        <h1 className="page-title mt-2">Terms</h1>
      </div>
      <div className="app-card space-y-4 p-6 text-[15px] leading-relaxed text-ink-muted sm:p-7">
        <p>Nigehban provides informational verification only. Use results at your own discretion.</p>
        <p>Abuse, spam, or automated scraping may result in rate limits.</p>
      </div>
    </div>
  );
}
