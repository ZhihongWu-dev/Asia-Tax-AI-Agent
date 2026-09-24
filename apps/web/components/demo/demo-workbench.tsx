"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ResultView } from "@/components/demo/result-view";
import { type AnalysisResult, type Meta, type SampleCase, WATERMARK_EN } from "@/lib/fsie";

const PIPELINE_STEPS = [
  "Extract candidate facts with the language model",
  "Check them against the 43-field dictionary",
  "Run the deterministic FSIE rule chain",
  "Attach statutory text and sources",
];

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg?: string }) => d.msg).join("; ");
  } catch {
    // fall through
  }
  return `The API answered ${response.status}. Is it running? Start it with: make run-api`;
}

function MetaStrip({ meta, error }: { meta: Meta | null; error: string | null }) {
  if (error) {
    return <p className="text-sm font-mono text-destructive">API offline: start it with make run-api</p>;
  }
  if (!meta) return <p className="text-sm font-mono text-muted-foreground">Connecting to the local API…</p>;
  const items = [
    `model ${meta.model ?? "not configured"}`,
    `rules v${meta.rule_set_version ?? "?"} (${meta.rule_set_status})`,
    `${meta.chain_nodes_implemented} / ${meta.chain_nodes_total} chain steps`,
    `${meta.legal_units} legal units from ${meta.sources_parsed} sources`,
    `coverage cutoff ${meta.legal_coverage_cutoff ?? "?"}`,
  ];
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono text-muted-foreground">
      {items.map((item) => (
        <span key={item} className="flex items-center gap-4">
          <span>{item}</span>
          <span className="text-foreground/20 last:hidden">/</span>
        </span>
      ))}
    </p>
  );
}

function EmptyState() {
  return (
    <div className="border border-dashed border-foreground/20 p-10 lg:p-14">
      <h2 className="text-4xl font-display tracking-tight mb-6">Nothing run yet.</h2>
      <p className="text-muted-foreground leading-relaxed max-w-xl mb-10">
        Choose a preset on the left or write a fictional case, then press Analyze. The result shows the
        candidate facts, every step of the rule chain, what a human still has to decide, and the statutory text.
      </p>
      <ol className="grid gap-4">
        {PIPELINE_STEPS.map((step, index) => (
          <li key={step} className="flex items-center gap-4 text-sm">
            <span className="w-8 h-8 flex items-center justify-center border border-foreground/20 font-mono text-xs">
              {index + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}

function RunningState({ seconds }: { seconds: number }) {
  return (
    <div className="border border-foreground/20 p-10 lg:p-14">
      <div className="flex items-center gap-3 text-sm font-mono text-muted-foreground mb-8">
        <Loader2 className="w-4 h-4 animate-spin" />
        Running · {seconds}s
      </div>
      <ol className="grid gap-4">
        {PIPELINE_STEPS.map((step, index) => (
          <li key={step} className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="w-8 h-8 flex items-center justify-center border border-foreground/20 font-mono text-xs">
              {index + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>
      <p className="mt-8 text-xs font-mono text-muted-foreground">
        Only step 1 calls a model; it usually takes 5 to 10 seconds.
      </p>
    </div>
  );
}

export function DemoWorkbench() {
  const [samples, setSamples] = useState<SampleCase[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SampleCase | null>(null);
  const [text, setText] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [running, setRunning] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [resultExpected, setResultExpected] = useState<SampleCase["expected_state"]>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/samples")
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((data) => setSamples(data.cases ?? []))
      .catch(() => setSamples([]));
    fetch("/api/meta")
      .then(async (r) => (r.ok ? r.json() : Promise.reject(await readError(r))))
      .then(setMeta)
      .catch((reason) => setMetaError(String(reason)));
  }, []);

  useEffect(() => {
    if (!running) return;
    setSeconds(0);
    const started = Date.now();
    const interval = setInterval(() => setSeconds(Math.round((Date.now() - started) / 1000)), 500);
    return () => clearInterval(interval);
  }, [running]);

  const choose = (sample: SampleCase) => {
    setSelected(sample);
    setText(sample.text);
    setConfirmed(true); // presets are fictional by construction
    setError(null);
  };

  const run = async (caseText: string, isConfirmed: boolean, sample: SampleCase | null) => {
    setRunning(true);
    setError(null);
    try {
      const sampleId = sample && sample.text === caseText ? sample.id : null;
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: caseText, confirm_synthetic: isConfirmed, sample_id: sampleId }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setResult(await response.json());
      setResultExpected(sampleId && sample ? sample.expected_state : null);
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const analyze = () => run(text, confirmed, selected);

  // Shareable links: /demo?preset=<id> loads a preset, &run=1 also runs it.
  const autoRan = useRef(false);
  useEffect(() => {
    if (autoRan.current || samples.length === 0) return;
    const params = new URLSearchParams(window.location.search);
    const preset = samples.find((s) => s.id === params.get("preset"));
    if (!preset) return;
    autoRan.current = true;
    choose(preset);
    if (params.get("run") === "1") void run(preset.text, true, preset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [samples]);

  const tooShort = text.trim().length < 20;

  return (
    <div className="max-w-[1400px] mx-auto px-6 lg:px-12 pt-32 pb-24">
      <div className="mb-10">
        <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
          <span className="w-8 h-px bg-foreground/30" />
          Live demo · local
        </span>
        <h1 className="text-5xl lg:text-7xl font-display tracking-tight leading-[0.95] mb-6">
          Run a case through the chain.
        </h1>
        <MetaStrip meta={meta} error={metaError} />
      </div>

      <div className="mb-12 border border-foreground/15 bg-foreground/[0.02] px-5 py-3 text-sm">
        <span className="font-mono text-xs mr-3">L0</span>
        {WATERMARK_EN}
      </div>

      <div className="grid lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)] gap-12 lg:gap-16 items-start">
        {/* Case panel */}
        <div className="lg:sticky lg:top-28 grid gap-8">
          <div>
            <div className="text-sm font-medium mb-3">Presets</div>
            <div className="border border-foreground/10 divide-y divide-foreground/10 max-h-[340px] overflow-y-auto">
              {samples.length === 0 && (
                <p className="px-4 py-3 text-sm text-muted-foreground">No presets loaded (is the API running?).</p>
              )}
              {samples.map((sample) => (
                <button
                  key={sample.id}
                  type="button"
                  onClick={() => choose(sample)}
                  className={`w-full text-left px-4 py-3 transition-colors ${
                    selected?.id === sample.id ? "bg-foreground text-background" : "hover:bg-foreground/[0.03]"
                  }`}
                >
                  <div className="text-sm font-medium">{sample.title}</div>
                  <div
                    className={`text-xs font-mono mt-0.5 ${
                      selected?.id === sample.id ? "text-background/60" : "text-muted-foreground"
                    }`}
                  >
                    {sample.tag}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="case-text" className="text-sm font-medium mb-3 block">
              Case description
            </label>
            <textarea
              id="case-text"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (selected && e.target.value !== selected.text) setConfirmed(false);
              }}
              rows={11}
              maxLength={4000}
              placeholder="Fictional case for research only. A Hong Kong company, member of a multinational group, received a dividend from a foreign company it holds 20% of…"
              className="w-full resize-y border border-foreground/15 bg-background px-4 py-3 text-sm leading-relaxed focus:outline-none focus:border-foreground"
            />
            <div className="mt-1 text-right text-xs font-mono text-muted-foreground">{text.length} / 4000</div>
          </div>

          <label className="flex items-start gap-3 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="mt-1 accent-foreground"
            />
            <span>
              This case is fictional and contains no real client or personal data.
              <span className="block text-xs text-muted-foreground mt-1">
                Required at L0: only synthetic data may be sent to the model.
              </span>
            </span>
          </label>

          <Button
            type="button"
            onClick={analyze}
            disabled={running || tooShort || !confirmed}
            size="lg"
            className="bg-foreground hover:bg-foreground/90 text-background h-14 text-base rounded-full group"
          >
            {running ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Analyzing…
              </>
            ) : (
              <>
                Analyze
                <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
              </>
            )}
          </Button>

          {error && (
            <p role="alert" className="border border-destructive px-4 py-3 text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        {/* Results */}
        <div ref={resultRef} className="scroll-mt-28 min-w-0">
          {running ? (
            <RunningState seconds={seconds} />
          ) : result ? (
            <ResultView result={result} expected={resultExpected} />
          ) : (
            <EmptyState />
          )}
        </div>
      </div>
    </div>
  );
}
