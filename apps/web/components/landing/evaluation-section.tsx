"use client";

import { useEffect, useRef, useState } from "react";
import { useInView } from "@/lib/use-in-view";

function AnimatedCounter({ end, suffix = "" }: { end: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          const duration = 1600;
          const startTime = performance.now();
          const animate = (currentTime: number) => {
            const progress = Math.min((currentTime - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.round(eased * end));
            if (progress < 1) requestAnimationFrame(animate);
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.5 },
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, hasAnimated]);

  return (
    <div ref={ref} className="text-6xl lg:text-8xl font-display tracking-tight">
      {count.toLocaleString("en-US")}
      {suffix}
    </div>
  );
}

// Measured on the local build (make run-eval, make test, pytest -m integration).
const metrics = [
  { value: 10, suffix: " / 10", label: "Synthetic golden cases reproduce exactly" },
  { value: 8, suffix: " / 8", label: "English presets reach their expected state on the live model (best of two); injection preset absorbed" },
  { value: 92, suffix: "", label: "Offline tests: contracts, rules, API, guardrails" },
  { value: 22, suffix: " / 22", label: "Live tests passing: database, migrations, model, injection" },
];

export function EvaluationSection() {
  const [sectionRef, isVisible] = useInView<HTMLElement>();

  return (
    <section id="evaluation" ref={sectionRef} className="relative py-24 lg:py-32 border-y border-foreground/10">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8 mb-16 lg:mb-24">
          <div>
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
              <span className="w-8 h-px bg-foreground/30" />
              Evaluation
            </span>
            <h2
              className={`text-4xl lg:text-6xl font-display tracking-tight transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              Measured,
              <br />
              <span className="text-muted-foreground">not claimed.</span>
            </h2>
          </div>
          <p className="max-w-md font-mono text-sm text-muted-foreground">
            Engineering checks only. Passing them shows the pipeline behaves as designed;
            it does not show the tax reasoning is correct. That needs a Hong Kong tax expert.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-foreground/10">
          {metrics.map((metric, index) => (
            <div
              key={metric.label}
              className={`bg-background p-8 lg:p-12 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              <AnimatedCounter end={metric.value} suffix={metric.suffix} />
              <div className="mt-4 text-lg text-muted-foreground">{metric.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
