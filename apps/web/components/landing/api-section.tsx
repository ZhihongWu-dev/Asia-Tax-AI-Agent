"use client";

import { useState } from "react";
import Link from "next/link";
import { Copy, Check } from "lucide-react";
import { useInView } from "@/lib/use-in-view";

const codeExamples = [
  {
    label: "Request",
    code: `curl -s localhost:8000/api/analyze \\
  -H 'content-type: application/json' \\
  -d '{
    "text": "Fictional case ...",
    "confirm_synthetic": true
  }'`,
  },
  {
    label: "Response",
    code: `{
  "terminal_state": "human_review_required",
  "blockers": ["foreign_tax_on_...",
               "main_purpose_tax_benefit_flag"],
  "chain": [{ "node": "receipt",
              "output": "satisfied", ... }],
  "model": "deepseek-flash",
  "rule_set_version": "0.2.1",
  "engine_commit": "…",
  "execution_batch": "NL-5e809a5c72:986c..."
}`,
  },
  {
    label: "Run locally",
    code: `make db-up migrate load knowledge-build
make run-api          # FastAPI on :8000

cd apps/web
pnpm install && pnpm dev   # :3000`,
  },
];

const features = [
  { title: "Structured facts", description: "Every candidate fact with its status and statute." },
  { title: "Every chain step", description: "Including the ones not implemented yet." },
  { title: "Statutory text", description: "The subsections behind the participation thresholds." },
  { title: "Traceable", description: "Model, prompt, rule package and engine commit on every run." },
];

const codeAnimationStyles = `
  .dev-code-line {
    opacity: 0;
    transform: translateX(-8px);
    animation: devLineReveal 0.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  }
  @keyframes devLineReveal {
    to { opacity: 1; transform: translateX(0); }
  }
`;

export function ApiSection() {
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const [sectionRef, isVisible] = useInView<HTMLElement>();

  const handleCopy = () => {
    navigator.clipboard.writeText(codeExamples[activeTab].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="api" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <style dangerouslySetInnerHTML={{ __html: codeAnimationStyles }} />
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-start">
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
              <span className="w-8 h-px bg-foreground/30" />
              Local API
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-8">
              One endpoint.
              <br />
              <span className="text-muted-foreground">Full provenance.</span>
            </h2>
            <p className="text-xl text-muted-foreground mb-12 leading-relaxed">
              The web demo is a thin client over a FastAPI service. The CLI and the API run
              the same analysis, and every response says which model, prompt, rule package
              and engine commit produced it.
            </p>

            <div className="grid grid-cols-2 gap-6">
              {features.map((feature, index) => (
                <div
                  key={feature.title}
                  className={`transition-all duration-500 ${
                    isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
                  }`}
                  style={{ transitionDelay: `${index * 50 + 200}ms` }}
                >
                  <h3 className="font-medium mb-1">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div
            className={`lg:sticky lg:top-32 transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"
            }`}
          >
            <div className="border border-foreground/10">
              <div className="flex items-center border-b border-foreground/10">
                {codeExamples.map((example, idx) => (
                  <button
                    key={example.label}
                    type="button"
                    onClick={() => setActiveTab(idx)}
                    className={`px-6 py-4 text-sm font-mono transition-colors relative ${
                      activeTab === idx ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {example.label}
                    {activeTab === idx && <span className="absolute bottom-0 left-0 right-0 h-px bg-foreground" />}
                  </button>
                ))}
                <div className="flex-1" />
                <button
                  type="button"
                  onClick={handleCopy}
                  className="px-4 py-4 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label="Copy code"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>

              <div className="p-8 font-mono text-sm bg-foreground/[0.01] min-h-[260px] overflow-x-auto">
                <pre className="text-foreground/80">
                  {codeExamples[activeTab].code.split("\n").map((line, lineIndex) => (
                    <div
                      key={`${activeTab}-${lineIndex}`}
                      className="leading-loose dev-code-line whitespace-pre"
                      style={{ animationDelay: `${lineIndex * 60}ms` }}
                    >
                      {line || " "}
                    </div>
                  ))}
                </pre>
              </div>
            </div>

            <div className="mt-6 flex items-center gap-6 text-sm">
              <Link href="/demo" className="text-foreground hover:underline underline-offset-4">
                Open the demo
              </Link>
              <span className="text-foreground/20">|</span>
              <a
                href="https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent"
                className="text-muted-foreground hover:text-foreground"
                target="_blank"
                rel="noreferrer"
              >
                View the repository
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
