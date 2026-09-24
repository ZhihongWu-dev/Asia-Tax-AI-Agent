"use client";

import { useInView } from "@/lib/use-in-view";

const components = [
  { name: "DeepSeek V4.1 Flash", role: "id deepseek-flash · fact extraction" },
  { name: "Fact dictionary", role: "43 fields · 26 evidence types" },
  { name: "Rule engine", role: "Pure Python evaluators" },
  { name: "PostgreSQL", role: "Facts, runs, audit events" },
  { name: "pgvector", role: "Extension, reserved for retrieval" },
  { name: "Alembic", role: "Schema migrations" },
  { name: "FastAPI", role: "Local API" },
  { name: "HK e-Legislation", role: "Cap. 112 as XML" },
  { name: "Inland Revenue Dept.", role: "Guidance and rulings" },
  { name: "Next.js", role: "This web demo" },
  { name: "pytest", role: "Offline and live tests" },
  { name: "Docker", role: "Local database" },
];

export function StackSection() {
  const [sectionRef, isVisible] = useInView<HTMLElement>();

  return (
    <section id="stack" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div
          className={`text-center max-w-3xl mx-auto mb-16 lg:mb-24 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
            <span className="w-8 h-px bg-foreground/30" />
            Under the hood
            <span className="w-8 h-px bg-foreground/30" />
          </span>
          <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-6">
            Plain components
            <br />
            you can read.
          </h2>
          <p className="text-xl text-muted-foreground">
            No agent framework and no hidden orchestration: one model step (at most one
            repair call), a rule engine and a database, wired together in code you can inspect.
          </p>
        </div>
      </div>

      <div className="w-full mb-6">
        <div className="flex gap-6 marquee">
          {[...Array(2)].map((_, setIndex) => (
            <div key={setIndex} className="flex gap-6 shrink-0">
              {components.map((item) => (
                <div
                  key={`${item.name}-${setIndex}`}
                  className="shrink-0 px-8 py-6 border border-foreground/10 hover:border-foreground/30 hover:bg-foreground/[0.02] transition-all duration-300 group"
                >
                  <div className="text-lg font-medium group-hover:translate-x-1 transition-transform">{item.name}</div>
                  <div className="text-sm text-muted-foreground">{item.role}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="w-full">
        <div className="flex gap-6 marquee-reverse">
          {[...Array(2)].map((_, setIndex) => (
            <div key={setIndex} className="flex gap-6 shrink-0">
              {[...components].reverse().map((item) => (
                <div
                  key={`${item.name}-reverse-${setIndex}`}
                  className="shrink-0 px-8 py-6 border border-foreground/10 hover:border-foreground/30 hover:bg-foreground/[0.02] transition-all duration-300 group"
                >
                  <div className="text-lg font-medium group-hover:translate-x-1 transition-transform">{item.name}</div>
                  <div className="text-sm text-muted-foreground">{item.role}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
