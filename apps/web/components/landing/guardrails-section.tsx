"use client";

import { Shield, Lock, Eye, FileCheck } from "lucide-react";
import { useInView } from "@/lib/use-in-view";

const guardrails = [
  {
    icon: Shield,
    title: "A watermark that cannot be removed",
    description: "Hard-coded into the report renderer, with no parameter to turn it off.",
  },
  {
    icon: Lock,
    title: "Validation cannot be forged",
    description: "The contract validator refuses any rule or source marked verified. Only a Hong Kong tax expert may make that change.",
  },
  {
    icon: Eye,
    title: "Prompt injection is absorbed",
    description: "Instructions hidden in a case cannot add fields or open the professional gate. One demo preset shows it happening.",
  },
  {
    icon: FileCheck,
    title: "Synthetic data only",
    description: "The API refuses cases not confirmed as fictional, in line with the L0 rule that only synthetic data reaches a model.",
  },
];

const tags = ["L0 research", "Unverified rules", "No tax opinions", "Synthetic data", "Runs locally"];

export function GuardrailsSection() {
  const [sectionRef, isVisible] = useInView<HTMLElement>();

  return (
    <section id="guardrails" ref={sectionRef} className="relative py-24 lg:py-32 bg-foreground/[0.02] overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24">
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
              <span className="w-8 h-px bg-foreground/30" />
              Guardrails
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-8">
              Safe to show
              <br />
              before it is useful.
            </h2>
            <p className="text-xl text-muted-foreground leading-relaxed mb-12">
              A research prototype in a professional-liability field has to be honest about
              what it is. These controls are enforced in code and covered by tests.
            </p>

            <div className="flex flex-wrap gap-3">
              {tags.map((tag, index) => (
                <span
                  key={tag}
                  className={`px-4 py-2 border border-foreground/10 text-sm font-mono transition-all duration-500 ${
                    isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                  }`}
                  style={{ transitionDelay: `${index * 50 + 200}ms` }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="grid gap-6">
            {guardrails.map((item, index) => (
              <div
                key={item.title}
                className={`p-6 border border-foreground/10 hover:border-foreground/20 transition-all duration-500 group ${
                  isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"
                }`}
                style={{ transitionDelay: `${index * 100}ms` }}
              >
                <div className="flex items-start gap-4">
                  <div className="shrink-0 w-10 h-10 flex items-center justify-center border border-foreground/10 group-hover:bg-foreground group-hover:text-background transition-colors duration-300">
                    <item.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium mb-1 group-hover:translate-x-1 transition-transform duration-300">
                      {item.title}
                    </h3>
                    <p className="text-muted-foreground">{item.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
