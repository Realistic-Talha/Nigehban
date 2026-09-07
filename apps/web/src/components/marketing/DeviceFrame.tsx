"use client";

export function DeviceFrame({
  variant = "phone",
  children,
  className,
}: {
  variant?: "phone" | "desktop";
  children: React.ReactNode;
  className?: string;
}) {
  if (variant === "desktop") {
    return (
      <div
        className={`overflow-hidden rounded-[28px] border border-border bg-paper shadow-lift ${className ?? ""}`}
      >
        <div className="flex h-10 items-center border-b border-border bg-paper-2 px-4">
          <span className="text-[11px] text-ink-subtle">nigehban.app</span>
        </div>
        <div className="p-5 sm:p-6">{children}</div>
      </div>
    );
  }

  return (
    <div
      className={`mx-auto w-full max-w-[270px] overflow-hidden rounded-[36px] border-[7px] border-[#2a2a2a] bg-paper shadow-lift ${className ?? ""}`}
    >
      <div className="mx-auto mt-2.5 h-5 w-24 rounded-full bg-ink/10" aria-hidden />
      <div className="p-4 pb-8">{children}</div>
    </div>
  );
}
