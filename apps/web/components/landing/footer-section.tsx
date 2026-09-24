"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { AnimatedWave } from "./animated-wave";

const footerLinks: Record<string, { name: string; href: string; external?: boolean }[]> = {
  Prototype: [
    { name: "Demo", href: "/demo" },
    { name: "Pipeline", href: "/#how-it-works" },
    { name: "Guardrails", href: "/#guardrails" },
    { name: "Limits", href: "/#limits" },
  ],
  "Official sources": [
    { name: "Cap. 112 on HKeL", href: "https://www.elegislation.gov.hk/hk/cap112!en", external: true },
    { name: "IRD: FSIE regime", href: "https://www.ird.gov.hk/eng/tax/bus_fsie.htm", external: true },
    { name: "IRD: advance rulings", href: "https://www.ird.gov.hk/eng/ppr/arc.htm", external: true },
  ],
  Project: [
    { name: "Repository", href: "https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent", external: true },
    { name: "Local API", href: "/#api" },
  ],
};

export function FooterSection() {
  return (
    <footer className="relative border-t border-foreground/10">
      <div className="absolute inset-0 h-64 opacity-20 pointer-events-none overflow-hidden">
        <AnimatedWave />
      </div>

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
        <div className="py-16 lg:py-24">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-12 lg:gap-8">
            <div className="col-span-2">
              <Link href="/" className="inline-flex items-center gap-2 mb-6">
                <span className="text-2xl font-display">AsiaTax</span>
                <span className="text-xs text-muted-foreground font-mono">L0</span>
              </Link>
              <p className="text-muted-foreground leading-relaxed max-w-xs">
                A research prototype for Hong Kong&apos;s foreign-sourced income exemption
                regime, built to be checked rather than trusted.
              </p>
            </div>

            {Object.entries(footerLinks).map(([title, links]) => (
              <div key={title}>
                <h3 className="text-sm font-medium mb-6">{title}</h3>
                <ul className="space-y-4">
                  {links.map((link) => (
                    <li key={link.name}>
                      <a
                        href={link.href}
                        {...(link.external ? { target: "_blank", rel: "noreferrer" } : {})}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1 group"
                      >
                        {link.name}
                        {link.external && (
                          <ArrowUpRight className="w-3 h-3 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                        )}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="py-8 border-t border-foreground/10 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            L0 research prototype. Not tax advice. Not for use on client matters.
          </p>
          <span className="text-sm font-mono text-muted-foreground">Local build · synthetic data only</span>
        </div>
      </div>
    </footer>
  );
}
