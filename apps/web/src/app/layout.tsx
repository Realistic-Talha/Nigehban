import type { Metadata, Viewport } from "next";
import { Instrument_Serif, DM_Sans, Noto_Sans_Arabic } from "next/font/google";
import "@/styles/globals.css";
import { ThemeProvider } from "@/providers/theme-provider";
import { QueryProvider } from "@/providers/query-provider";
import { LocaleProvider } from "@/providers/locale-provider";
import { ServiceWorkerRegistrar } from "@/components/shell/ServiceWorkerRegistrar";

const instrument = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
  style: ["normal", "italic"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

const notoSansArabic = Noto_Sans_Arabic({
  subsets: ["arabic"],
  variable: "--font-noto-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Nigehban — Verify before you share",
  description:
    "AI-powered scam detection, fact-checking, and media verification for Pakistan.",
  manifest: "/manifest.json",
  icons: { icon: "/icon-192.png", apple: "/icon-192.png" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fdfcf0" },
    { media: "(prefers-color-scheme: dark)", color: "#121412" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${instrument.variable} ${dmSans.variable} ${notoSansArabic.variable}`}
    >
      <body className="flex min-h-dvh flex-col font-body antialiased">
        <ThemeProvider>
          <QueryProvider>
            <LocaleProvider>
              {children}
              <ServiceWorkerRegistrar />
            </LocaleProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
