import { ForceLightTheme } from "@/components/marketing/ForceLightTheme";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <ForceLightTheme>{children}</ForceLightTheme>;
}
