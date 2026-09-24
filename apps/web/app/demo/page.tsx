import type { Metadata } from "next";
import { Navigation } from "@/components/landing/navigation";
import { DemoWorkbench } from "@/components/demo/demo-workbench";

export const metadata: Metadata = {
  title: "Demo · AsiaTax Hong Kong FSIE research prototype",
  description: "Run a fictional Hong Kong foreign-sourced dividend case through the FSIE rule chain.",
};

export default function DemoPage() {
  return (
    <main className="relative min-h-screen overflow-x-clip noise-overlay">
      <Navigation />
      <DemoWorkbench />
    </main>
  );
}
