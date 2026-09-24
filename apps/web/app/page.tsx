import { Navigation } from "@/components/landing/navigation";
import { HeroSection } from "@/components/landing/hero-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { KnowledgeSection } from "@/components/landing/knowledge-section";
import { EvaluationSection } from "@/components/landing/evaluation-section";
import { StackSection } from "@/components/landing/stack-section";
import { GuardrailsSection } from "@/components/landing/guardrails-section";
import { ApiSection } from "@/components/landing/api-section";
import { LimitsSection } from "@/components/landing/limits-section";
import { CtaSection } from "@/components/landing/cta-section";
import { FooterSection } from "@/components/landing/footer-section";

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-x-hidden noise-overlay">
      <Navigation />
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <KnowledgeSection />
      <EvaluationSection />
      <StackSection />
      <GuardrailsSection />
      <ApiSection />
      <LimitsSection />
      <CtaSection />
      <FooterSection />
    </main>
  );
}
