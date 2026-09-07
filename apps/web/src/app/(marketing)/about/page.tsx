import { MarketingNav } from "@/components/marketing/MarketingNav";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import { Card } from "@/components/ui/Card";

export default function AboutPage() {
  return (
    <>
      <MarketingNav />
      <main className="page-shell max-w-2xl space-y-10 py-12 sm:py-16">
        <div>
          <p className="page-eyebrow">About</p>
          <h1 className="page-title mt-2">How Nigehban works</h1>
        </div>

        <Card className="app-card !bg-white space-y-4 p-6 sm:p-7">
          <p className="text-[15px] leading-relaxed text-ink-muted">
            Nigehban runs a multi-agent pipeline: intake, specialized analysis, verdict synthesis, and
            a judge that enforces confidence thresholds before publishing a result.
          </p>
          <ol className="list-decimal space-y-2 ps-5 text-sm text-ink-muted">
            <li>Submit text, a scam message, or media.</li>
            <li>Agents extract signals, search evidence, and match known patterns.</li>
            <li>A judge reviews the draft and may downgrade low-confidence outputs.</li>
            <li>Results are stored with a full agent audit trail.</li>
          </ol>
        </Card>

        <section className="space-y-3">
          <h2 className="font-display text-2xl">Verdict labels</h2>
          <ul className="space-y-2 text-sm text-ink-muted">
            <li>
              <strong className="text-ink">True / Safe</strong> — supported by evidence or low risk.
            </li>
            <li>
              <strong className="text-ink">False / Scam</strong> — contradicts sources or matches fraud
              patterns.
            </li>
            <li>
              <strong className="text-ink">Misleading</strong> — partially true but missing context.
            </li>
            <li>
              <strong className="text-ink">Unverified</strong> — insufficient evidence to decide.
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="font-display text-2xl">Limitations</h2>
          <p className="text-sm text-ink-muted">
            Automated checks can be wrong. Always verify critical decisions with official sources
            (SBP, FIA, banks). Nigehban is not legal advice.
          </p>
        </section>
      </main>
      <MarketingFooter />
    </>
  );
}
