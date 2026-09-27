import { useEffect, useRef, useState } from "react";
import { api, ApiError, type FactPatch } from "../api";
import type { Case, FieldSpec } from "../workspace";

export function useWorkspace() {
  const [cases, setCases] = useState<Case[]>([]),
    [fields, setFields] = useState<FieldSpec[]>([]);
  const [activeId, setActiveId] = useState(location.hash.slice(1));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const locked = useRef(false);
  const retryRef = useRef<(() => Promise<void>) | null>(null);
  const boot = useRef<Promise<{ cases: Case[]; fields: FieldSpec[] }> | null>(
    null,
  );
  const current = cases.find((c) => c.id === activeId) || cases[0];
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  async function initialize() {
    const session = await api.session();
    const list = await api.list();
    return {
      fields: session.fields,
      cases: list.length ? list : [await api.create()],
    };
  }
  useEffect(() => {
    let live = true;
    boot.current ||= initialize();
    boot.current
      .then((data) => {
        if (live) {
          setCases(data.cases);
          setFields(data.fields);
        }
      })
      .catch((e) => {
        if (live) setError(e.code || "service_unavailable");
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (current) history.replaceState(null, "", `#${current.id}`);
  }, [current?.id]);
  function update(next: Case) {
    setCases((all) => all.map((c) => (c.id === next.id ? next : c)));
  }
  async function perform(operation: () => Promise<void>) {
    if (locked.current) return false;
    locked.current = true;
    setBusy(true);
    setError("");
    retryRef.current = operation;
    try {
      await operation();
      retryRef.current = null;
      return true;
    } catch (e) {
      setError(e instanceof ApiError ? e.code : "service_unavailable");
      return false;
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }
  async function mutate(
    doc: Case,
    action: "messages" | "facts" | "confirm" | "analyze",
    payload: Record<string, unknown>,
    requestId: string,
  ) {
    try {
      const next = await api.mutate(doc, action, payload, requestId);
      update(next);
      return next;
    } catch (e) {
      if (e instanceof ApiError && e.code === "revision_conflict") {
        update(await api.get(doc.id));
      }
      throw e;
    }
  }
  function send(text: string, approved: boolean) {
    const doc = current,
      requestId = crypto.randomUUID();
    return perform(async () => {
      await mutate(
        doc,
        "messages",
        { text, data_approved: approved },
        requestId,
      );
      setDrafts((all) =>
        all[doc.id]?.trim() === text ? { ...all, [doc.id]: "" } : all,
      );
    });
  }
  function save(patch: FactPatch) {
    const doc = current,
      requestId = crypto.randomUUID();
    return perform(async () => {
      await mutate(doc, "facts", { facts: patch }, requestId);
    });
  }
  function confirmAndAnalyze() {
    const doc = current,
      confirmId = crypto.randomUUID(),
      runId = crypto.randomUUID();
    // Keep the confirmed response for retries so a completed confirmation is not repeated.
    let confirmed: Case | null = null;
    return perform(async () => {
      confirmed ||= await mutate(doc, "confirm", {}, confirmId);
      await mutate(confirmed, "analyze", {}, runId);
    });
  }
  function analyze() {
    const doc = current,
      requestId = crypto.randomUUID();
    return perform(async () => {
      await mutate(doc, "analyze", {}, requestId);
    });
  }
  function newCase() {
    return perform(async () => {
      const next = await api.create();
      setCases((all) => [next, ...all]);
      setActiveId(next.id);
    });
  }
  function changeDraft(text: string) {
    setDrafts((all) => ({ ...all, [current.id]: text }));
  }
  function retry() {
    if (!current) {
      boot.current = null;
      location.reload();
      return;
    }
    if (retryRef.current) void perform(retryRef.current);
  }
  return {
    cases,
    current,
    fields,
    busy,
    error,
    setActiveId,
    drafts,
    changeDraft,
    send,
    save,
    confirmAndAnalyze,
    analyze,
    newCase,
    retry,
  };
}
