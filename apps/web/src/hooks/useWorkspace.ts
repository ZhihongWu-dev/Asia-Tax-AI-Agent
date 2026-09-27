import { useEffect, useRef, useState } from "react";
import { api, ApiError, type FactPatch } from "../api";
import type { Case, FieldSpec, Message } from "../workspace";

export function useWorkspace() {
  const [cases, setCases] = useState<Case[]>([]),
    [fields, setFields] = useState<FieldSpec[]>([]);
  const [activeId, setActiveId] = useState(location.hash.slice(1));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [errorCaseId, setErrorCaseId] = useState("");
  const locked = useRef(false);
  const retryRef = useRef<{
    operation: () => Promise<void>;
    caseId: string;
  } | null>(null);
  const [workingCaseId, setWorkingCaseId] = useState("");
  const [outbox, setOutbox] = useState<{ caseId: string; message: Message }[]>(
    [],
  );
  const boot = useRef<Promise<{ cases: Case[]; fields: FieldSpec[] }> | null>(
    null,
  );
  const storedCurrent = cases.find((c) => c.id === activeId) || cases[0];
  const localMessages = outbox
    .filter((item) => item.caseId === storedCurrent?.id)
    .map((item) => item.message);
  const current =
    storedCurrent && localMessages.length
      ? {
          ...storedCurrent,
          messages: [...storedCurrent.messages, ...localMessages],
        }
      : storedCurrent;
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
  async function perform(
    operation: () => Promise<void>,
    caseId = current?.id || "",
  ) {
    if (locked.current) return false;
    locked.current = true;
    setBusy(true);
    setWorkingCaseId(caseId);
    setErrorCaseId(caseId);
    setError("");
    retryRef.current = { operation, caseId };
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
      setWorkingCaseId("");
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
    const doc = storedCurrent,
      requestId = crypto.randomUUID();
    return perform(async () => {
      const localId = `pending-${requestId}`;
      setOutbox((all) => [
        ...all.filter(
          (item) =>
            item.message.id !== localId &&
            !(
              item.caseId === doc.id &&
              item.message.delivery === "failed" &&
              item.message.text === text
            ),
        ),
        {
          caseId: doc.id,
          message: { id: localId, role: "user", text, delivery: "sending" },
        },
      ]);
      setDrafts((all) =>
        all[doc.id]?.trim() === text ? { ...all, [doc.id]: "" } : all,
      );
      try {
        await mutate(
          doc,
          "messages",
          { text, data_approved: approved },
          requestId,
        );
        setOutbox((all) => all.filter((item) => item.message.id !== localId));
      } catch (e) {
        setOutbox((all) =>
          all.map((item) =>
            item.message.id === localId
              ? { ...item, message: { ...item.message, delivery: "failed" } }
              : item,
          ),
        );
        // Preserve a new draft typed during the request; the failed bubble retains the old text.
        setDrafts((all) => (all[doc.id] ? all : { ...all, [doc.id]: text }));
        throw e;
      }
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
    if (retryRef.current)
      void perform(retryRef.current.operation, retryRef.current.caseId);
  }
  return {
    cases,
    current,
    fields,
    busy,
    currentBusy: busy && workingCaseId === current?.id,
    error: !current || errorCaseId === current.id ? error : "",
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
