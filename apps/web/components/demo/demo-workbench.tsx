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

// The API's own error details are passed through, except the extraction
// rejection, whose detail comes from the (Chinese) contract validator.
async function readError(response: Response): Promise<string> {
  let detail: unknown = null;
  try {
    detail = (await response.json()).detail;
  } catch {
    // Not JSON: the Next.js proxy could not get an answer from the API.
    return `No usable answer from the API (HTTP ${response.status}). If it is running, check its terminal for errors; otherwise start it with make run-api.`;
  }
  if (response.status === 422 && typeof detail === "string" && detail.startsWith("extraction rejected")) {
    return "The model's candidate facts still broke the fact dictionary after one repair round, so the case was rejected. Try rephrasing the case.";
  }
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ") || `Request rejected (HTTP ${response.status}).`;
  }
  return `The API answered HTTP ${response.status}.`;
}

function MetaStrip({ meta, error }: { meta: Meta | null; error: string | null }) {
  if (error) return <p className="text-sm font-mono text-destructive">{error}</p>;
  if (!meta) return <p className="text-sm font-mono text-muted-foreground">Connecting to the local API…</p>;
  const items = [
    `model ${meta.model ?? "not configured"}`,
    `rules v${meta.rule_set_version ?? "?"} (${meta.rule_set_status ?? "?"})`,
    `${meta.chain_nodes_implemented} / ${meta.chain_nodes_total} chain steps`,
    `${meta.legal_units} legal units from ${meta.sources_parsed} sources`,
    `coverage cutoff ${meta.legal_coverage_cutoff ?? "?"}`,
  ];
  return (
    <p className="flex flex-wrap gap-y-1 text-xs font-mono text-muted-foreground">
      {items.map((item, index) => (
        <span key={item} className="whitespace-nowrap">
          {index > 0 && <span className="mx-3 text-foreground/20">/</span>}
          {item}
        </span>
      ))}
    </p>
  );
}

function StepList({ muted }: { muted?: boolean }) {
  return (
    <ol className="grid gap-4">
      {PIPELINE_STEPS.map((step, index) => (
        <li key={step} className={`flex items-center gap-4 text-sm ${muted ? "text-muted-foreground" : ""}`}>
          <span className="w-8 h-8 flex items-center justify-center border border-foreground/20 font-mono text-xs">
            {index + 1}
          </span>
          {step}
        </li>
      ))}
    </ol>
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
      <StepList />
    </div>
  );
}

function RunningState({ seconds }: { seconds: number }) {
  return (
    <div className="border border-foreground/20 p-10 lg:p-14" aria-live="polite">
      <div className="flex items-center gap-3 text-sm font-mono text-muted-foreground mb-8">
        <Loader2 className="w-4 h-4 animate-spin" />
        Running · {seconds}s
      </div>
      <StepList muted />
      <p className="mt-8 text-xs font-mono text-muted-foreground">
        Only step 1 calls a model (at most twice, if its first answer needs repair); it usually takes 5 to 10 seconds.
      </p>
    </div>
  );
}

interface Analysis {
  result: AnalysisResult;
  text: string;
  sample: SampleCase | null;
}

export function DemoWorkbench() {
  const [samples, setSamples] = useState<SampleCase[]>([]);
  const [samplesState, setSamplesState] = useState<"loading" | "ready" | "failed">("loading");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SampleCase | null>(null);
  const [text, setText] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [running, setRunning] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const inFlight = useRef(false);

  useEffect(() => {
    fetch("/api/samples")
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((data) => {
        setSamples(data.cases ?? []);
        setSamplesState("ready");
      })
      .catch(() => setSamplesState("failed"));
    fetch("/api/meta")
      .then(async (r) => (r.ok ? r.json() : Promise.reject(await readError(r))))
      .then(setMeta)
      .catch((reason) =>
        setMetaError(typeof reason === "string" ? reason : "API offline: start it with make run-api"),
      );
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
    if (inFlight.current) return;
    inFlight.current = true;
    setRunning(true);
    setError(null);
    setAnalysis(null);
    const matchedSample = sample && sample.text === caseText ? sample : null;
    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: caseText, confirm_synthetic: isConfirmed, sample_id: matchedSample?.id ?? null }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setAnalysis({ result: await response.json(), text: caseText, sample: matchedSample });
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      inFlight.current = false;
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
  const stale = analysis !== null && analysis.text !== text;

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
        <div className="lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto lg:pr-2 grid gap-8">
          <div>
            <div className="text-sm font-medium mb-3">Presets</div>
            <div className="border border-foreground/10 divide-y divide-foreground/10 max-h-[300px] overflow-y-auto">
              {samplesState === "loading" && <p className="px-4 py-3 text-sm text-muted-foreground">Loading presets…</p>}
              {samplesState === "failed" && (
                <p className="px-4 py-3 text-sm text-muted-foreground">Presets unavailable: is the API running?</p>
              )}
              {samples.map((sample) => (
                <button
                  key={sample.id}
                  type="button"
                  disabled={running}
                  onClick={() => choose(sample)}
                  aria-pressed={selected?.id === sample.id}
                  className={`w-full text-left px-4 py-3 transition-colors disabled:cursor-not-allowed ${
                    selected?.id === sample.id ? "bg-foreground text-background" : "hover:bg-foreground/[0.03]"
                  }`}
                >
                  <div className="text-sm font-medium">{sample.title}</div>
                  <div
                    className={`text-xs font-mono mt-0.5 ${
                      selected?.id === sample.id ? "text-background/70" : "text-muted-foreground"
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
              disabled={running}
              onChange={(e) => {
                setText(e.target.value);
                if (selected && e.target.value !== selected.text) setConfirmed(false);
              }}
              rows={9}
              maxLength={4000}
              placeholder="Fictional case for research only. A company that carries on business in Hong Kong, member of a multinational group, received a dividend from a foreign company it holds 20% of…"
              className="w-full resize-y border border-foreground/15 bg-background px-4 py-3 text-sm leading-relaxed focus:outline-none focus:border-foreground disabled:opacity-60"
            />
            <div className="mt-1 text-right text-xs font-mono text-muted-foreground">{text.length} / 4000</div>
          </div>

          <label className="flex items-start gap-3 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              disabled={running}
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
          ) : analysis ? (
            <div className={stale ? "opacity-50" : ""}>
              {stale && (
                <p className="mb-6 border border-foreground/20 px-4 py-3 text-sm font-mono">
                  This result is for {analysis.sample ? `the preset "${analysis.sample.title}"` : "an earlier version of the case"};
                  the case text has changed since. Press Analyze to run the current text.
                </p>
              )}
              <ResultView result={analysis.result} expected={analysis.sample?.expected_state ?? null} />
            </div>
          ) : (
            <EmptyState />
          )}
        </div>
      </div>
    </div>
  );
}
