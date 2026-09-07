"use client";

import { MarketingNav } from "@/components/marketing/MarketingNav";
import { Hero } from "@/components/marketing/Hero";
import { DemoArc } from "@/components/marketing/DemoArc";
import { VerdictMarquee } from "@/components/marketing/VerdictMarquee";
import { FeatureSplit } from "@/components/marketing/FeatureSplit";
import { AgentBento } from "@/components/marketing/AgentBento";
import { ProductBento } from "@/components/marketing/ProductBento";
import { MidCta } from "@/components/marketing/MidCta";
import { ProofLetters } from "@/components/marketing/ProofLetters";
import { HowSteps } from "@/components/marketing/HowSteps";
import { CloseBand } from "@/components/marketing/CloseBand";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";

export default function HomePage() {
  return (
    <>
      <MarketingNav />
      <main>
        <Hero />
        <DemoArc />
        <VerdictMarquee />
        <FeatureSplit />
        <AgentBento />
        <ProductBento />
        <MidCta />
        <ProofLetters />
        <HowSteps />
        <CloseBand />
      </main>
      <MarketingFooter />
    </>
  );
}
