"use client";

import { useEffect, useState } from "react";
import { useInView } from "@/lib/use-in-view";

// Unit counts from the local knowledge build (make knowledge-build).
const sources = [
  { name: "Cap. 112, Part 4, Division 3A", origin: "HK e-Legislation · XML", units: "45 provisions" },
  { name: "2022 FSIE amendment ordinance", origin: "IRD · PDF", units: "62 pages" },
  { name: "IRD FSIE guidance page", origin: "IRD · HTML", units: "280 blocks" },
  { name: "IRD FSIE FAQ", origin: "IRD · HTML", units: "101 blocks" },
  { name: "IRD FSIE examples", origin: "IRD · HTML", units: "136 blocks" },
  { name: "Economic-substance advance ruling guide", origin: "IRD · HTML", units: "45 blocks" },
  { name: "Advance rulings 68, 72, 74, 75", origin: "IRD · HTML", units: "50 blocks" },
];

export function KnowledgeSection() {
  const [sectionRef, isVisible] = useInView<HTMLElement>();
  const [active, setActive] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActive((prev) => (prev + 1) % sources.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="knowledge" ref={sectionRef} className="relative py-24 lg:py-32 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          <div
            className={`transition-all duration-700 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
              <span className="w-8 h-px bg-foreground/30" />
              Knowledge base
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight mb-8">
              Official sources,
              <br />
              fingerprinted.
            </h2>
            <p className="text-xl text-muted-foreground leading-relaxed mb-12">
              Every source comes from an official Hong Kong domain, is snapshotted once
              and fingerprinted with SHA-256. Text is split into citable legal units,
              so a result can point at the exact subsection it relies on. When an IRD page
              changes, the new version is stored with its own hash and the drift is logged.
            </p>

            <div className="grid grid-cols-3 gap-8">
              <div>
                <div className="text-4xl lg:text-5xl font-display mb-2">10</div>
                <div className="text-sm text-muted-foreground">Sources parsed</div>
              </div>
              <div>
                <div className="text-4xl lg:text-5xl font-display mb-2">719</div>
                <div className="text-sm text-muted-foreground">Legal units</div>
              </div>
              <div>
                <div className="text-4xl lg:text-5xl font-display mb-2 whitespace-nowrap">Sep &apos;26</div>
                <div className="text-sm text-muted-foreground">Legal coverage cutoff</div>
              </div>
            </div>
          </div>

          <div
            className={`transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"
            }`}
          >
            <div className="border border-foreground/10">
              <div className="px-6 py-4 border-b border-foreground/10 flex items-center justify-between">
                <span className="text-sm font-mono text-muted-foreground">Source manifest</span>
                <span className="text-xs font-mono text-muted-foreground">snapshot · sha-256</span>
              </div>
              <div>
                {sources.map((source, index) => (
                  <div
                    key={source.name}
                    className={`px-6 py-5 border-b border-foreground/5 last:border-b-0 flex items-center justify-between gap-6 transition-all duration-300 ${
                      active === index ? "bg-foreground/[0.02]" : ""
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <span
                        className={`w-2 h-2 shrink-0 rounded-full transition-colors duration-300 ${
                          active === index ? "bg-foreground" : "bg-foreground/20"
                        }`}
                      />
                      <div>
                        <div className="font-medium">{source.name}</div>
                        <div className="text-sm text-muted-foreground">{source.origin}</div>
                      </div>
                    </div>
                    <span className="font-mono text-sm text-muted-foreground whitespace-nowrap">{source.units}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
