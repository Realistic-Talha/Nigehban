import { ForceLightTheme } from "@/components/marketing/ForceLightTheme";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import { PageEnter } from "@/components/motion/PageEnter";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <ForceLightTheme>
      <MarketingNav />
      <main className="flex-1 bg-[#fdfcf0]">
        <PageEnter>{children}</PageEnter>
      </main>
      <MarketingFooter />
    </ForceLightTheme>
  );
}
