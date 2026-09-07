export default function PrivacyPage() {
  return (
    <div className="page-shell max-w-2xl space-y-6 py-12 sm:py-16">
      <div>
        <p className="page-eyebrow">Legal</p>
        <h1 className="page-title mt-2">Privacy</h1>
      </div>
      <div className="app-card space-y-4 p-6 text-[15px] leading-relaxed text-ink-muted sm:p-7">
        <p>
          Submissions are processed to generate verification results. Do not submit passwords or full
          CNIC numbers.
        </p>
        <p>Contact the project maintainers for data deletion requests.</p>
      </div>
    </div>
  );
}
