"use client";

import { useInView } from "@/lib/use-in-view";

const limits = [
  {
    number: "01",
    title: "Five of ten chain steps",
    description:
      "The regulated-financial-entity exclusion, the s.15N subject-to-tax and switch-over test, anti-hybrid, main purpose and filing duties are not implemented. When the participation thresholds are met, the foreign-tax (s.15N(2)) and main-purpose (s.15N(4)) questions go to a person; the financial-entity exclusion and filing duties are not checked at all.",
  },
  {
    number: "02",
    title: "No expert validation yet",
    description:
      "Every rule and threshold is a candidate reading of Cap. 112. None has been confirmed by a Hong Kong tax professional.",
  },
  {
    number: "03",
    title: "One jurisdiction, one income type",
    description:
      "Hong Kong only, foreign-sourced dividends only. The source country's tax facts (rates, withholding, deductibility) are not modelled.",
  },
  {
    number: "04",
    title: "Single-pass intake",
    description:
      "Facts are extracted once from the text. There is no follow-up interview, and candidate facts reach the rule chain without an adviser confirming them.",
  },
  {
    number: "05",
    title: "Citations, not retrieval",
    description:
      "Results quote the statutory subsections behind the rule thresholds. Guidance pages and rulings are indexed but not yet retrieved case by case.",
  },
  {
    number: "06",
    title: "Not tax advice",
    description:
      "Everything here is for internal research and engineering validation. Nothing should be used on a real client matter.",
  },
];

export function LimitsSection() {
  const [sectionRef, isVisible] = useInView<HTMLElement>();

  return (
    <section id="limits" ref={sectionRef} className="relative py-24 lg:py-32">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="mb-16 lg:mb-24">
          <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
            <span className="w-8 h-px bg-foreground/30" />
            Limits
          </span>
          <h2
            className={`text-4xl lg:text-6xl font-display tracking-tight transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            What it does not do.
            <br />
            <span className="text-muted-foreground">Yet.</span>
          </h2>
        </div>

        <div className="grid md:grid-cols-2 gap-px bg-foreground/10 border border-foreground/10">
          {limits.map((limit, index) => (
            <div
              key={limit.number}
              className={`bg-background p-8 lg:p-10 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: `${index * 80}ms` }}
            >
              <span className="font-mono text-sm text-muted-foreground">{limit.number}</span>
              <h3 className="text-2xl lg:text-3xl font-display mt-4 mb-3">{limit.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{limit.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
