import { withAttachments, type Attachment } from '../attachments';
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type FactPatch } from "../api";
import type { Case, FieldSpec, Message, EntryHint } from "../workspace";
import { useLocale, answerLanguage, type Locale } from "../locale";

function blankCase(): Case {
  return {id: `draft-${crypto.randomUUID()}`, title: '', revision: 0, state: 'collecting',
    messages: [], facts: {}, questions: [], analyses: [], confirmed_revision: null, data_approved: false};
}
const temporary = (doc: Case) => doc.id.startsWith('draft-');

export function useWorkspace() {
  const { locale } = useLocale();
  const [cases, setCases] = useState<Case[]>([]),
    [fields, setFields] = useState<FieldSpec[]>([]);
  const [activeId, setActiveId] = useState(location.hash.slice(1));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [errorCaseId, setErrorCaseId] = useState("");
  const [errorLocale, setErrorLocale] = useState<Locale>(locale);
  const locked = useRef(false);
  const materialized = useRef(new Map<string, Case>());
  const composerKeys = useRef(new Map<string, string>());
  const controller = useRef<AbortController | null>(null);
  const [partial, setPartial] = useState<{ caseId: string; text: string } | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const retryRef = useRef<{
    operation: () => Promise<void>;
    caseId: string;
    replyLocale: Locale;
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
  const [entrySelections, setEntrySelections] = useState<Record<string, { text: string; hint: EntryHint }>>({});
  function chooseSuggestion(text: string, hint: EntryHint) {
    setDrafts(all => ({ ...all, [current.id]: text }));
    setEntrySelections(all => ({ ...all, [current.id]: { text, hint } }));
  }
  async function initialize() {
    const session = await api.session();
    const list = await api.list();
    return {
      fields: session.fields,
      cases: list.length ? list : [blankCase()],
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
    if (current) history.replaceState(null, "", temporary(current) ? location.pathname + location.search : `#${current.id}`);
  }, [current?.id]);
  function update(next: Case) {
    setCases((all) => all.map((c) => (c.id === next.id ? next : c)));
  }
  async function persist(doc: Case): Promise<Case> {
    if (!temporary(doc)) return doc;
    const cached = materialized.current.get(doc.id);
    if (cached) return cached;
    const next = await api.create();
    materialized.current.set(doc.id, next);
    composerKeys.current.set(next.id, doc.id);
    setCases(all => all.map(item => item.id === doc.id ? next : item));
    setDrafts(all => { const copy = {...all, [next.id]: all[doc.id] || ''}; delete copy[doc.id]; return copy; });
    setEntrySelections(all => { const copy = {...all}; if (copy[doc.id]) copy[next.id] = copy[doc.id]; delete copy[doc.id]; return copy; });
    setActiveId(id => !id || id === doc.id ? next.id : id);
    setWorkingCaseId(next.id);
    setErrorCaseId(next.id);
    if (retryRef.current?.caseId === doc.id) retryRef.current.caseId = next.id;
    return next;
  }
  function prepareCase() {
    const doc = storedCurrent;
    return perform(async () => { await persist(doc); }, doc.id);
  }
  async function perform(
    operation: () => Promise<void>,
    caseId = current?.id || "",
    replyLocale: Locale = locale,
  ) {
    if (locked.current) return false;
    locked.current = true;
    setBusy(true);
    setWorkingCaseId(caseId);
    setErrorCaseId(caseId);
    setError("");
    setErrorLocale(replyLocale);
    retryRef.current = { operation, caseId, replyLocale };
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
    action: "messages" | "facts" | "confirm" | "analyze" | "organization",
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
  function send(text: string, approved: boolean, files: Attachment[] = []) {
    const messageText = withAttachments(text, files);
    let completed = false;
    let doc = storedCurrent;
    const requestId = crypto.randomUUID();
    const replyLocale = answerLanguage(text, doc.reply_locale, locale);
    const entryHint = entrySelections[doc.id]?.text.trim() === text ? entrySelections[doc.id].hint : "auto";
    const pending = doc.dialogue?.status === "active" ? doc.dialogue.pending : null;
    return perform(async () => {
      doc = await persist(doc);
      const localId = `pending-${requestId}`;
      setOutbox((all) => [
        ...all.filter(
          (item) =>
            item.message.id !== localId &&
            !(
              item.caseId === doc.id &&
              item.message.delivery === "failed" &&
              item.message.text === messageText
            ),
        ),
        {
          caseId: doc.id,
          message: { id: localId, role: "user", text: messageText, delivery: "sending", reply_locale: replyLocale },
        },
      ]);
      setDrafts((all) =>
        all[doc.id]?.trim() === text ? { ...all, [doc.id]: "" } : all,
      );
      try {
        const abort = new AbortController();
        controller.current = abort;
        setPartial({ caseId: doc.id, text: "" });
        const next = await api.stream(doc, messageText, approved, requestId, abort.signal, (chunk, reset) =>
          setPartial(previous => previous?.caseId === doc.id ? { ...previous, text: reset ? "" : previous.text + chunk } : previous),
          entryHint, files.length ? null : text.startsWith("结构答复：") ? doc.domain_workflow?.pending_question_id || null : pending?.id || null, replyLocale);
        update(next);
        completed = true;
        setEntrySelections(all => { const copy = { ...all }; delete copy[doc.id]; return copy; });
        setOutbox((all) => all.filter((item) => item.message.id !== localId));
      } catch (e) {
        if (e instanceof ApiError && e.code === "revision_conflict") update(await api.get(doc.id));
        if (controller.current?.signal.aborted) {
          setOutbox(all => all.filter(item => item.message.id !== localId));
          setDrafts(all => all[doc.id] ? all : { ...all, [doc.id]: text });
          // A turn already committed before cancellation remains authoritative.
          update(await api.get(doc.id));
          return;
        }
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
      } finally {
        controller.current = null;
        setPartial(null);
      }
    }, doc.id, replyLocale).then(success => success && completed);
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
    if (locked.current) return;
    const existing = cases.find(temporary);
    const next = existing || blankCase();
    if (!existing) setCases(all => [next, ...all]);
    setActiveId(next.id);
  }
  function changeDraft(text: string) {
    setDrafts((all) => ({ ...all, [current.id]: text }));
    setEntrySelections(all => { const copy = { ...all }; delete copy[current.id]; return copy; });
  }
  function deleteCase(id: string) {
    const doc = cases.find(c => c.id === id);
    if (!doc) return Promise.resolve(false);
    const requestId = crypto.randomUUID();
    let deleted = temporary(doc);
    return perform(async () => {
      if (!deleted) {
        try { await api.deleteCase(doc, requestId); }
        catch (e) {
          if (e instanceof ApiError && e.code === 'revision_conflict') update(await api.get(id));
          // A lost deletion response can be retried without resurrecting the case.
          if (!(e instanceof ApiError && e.code === 'case_not_found')) throw e;
        }
        deleted = true;
      }
      const remaining = cases.filter(c => c.id !== id);
      if (!remaining.length) remaining.push(blankCase());
      setCases(remaining);
      if (current?.id === id) setActiveId(remaining[0].id);
      setDrafts(all => { const next = {...all}; delete next[id]; return next; });
      setEntrySelections(all => { const next = {...all}; delete next[id]; return next; });
      setOutbox(all => all.filter(item => item.caseId !== id));
    }, id);
  }
  function organize(id: string, changes: { title?: string; archived?: boolean }) {
    const doc = cases.find(c => c.id === id);
    if (!doc) return Promise.resolve(false);
    const requestId = crypto.randomUUID();
    return perform(async () => { await mutate(await persist(doc), "organization", changes, requestId); }, id);
  }
  function retry() {
    if (!current) {
      boot.current = null;
      location.reload();
      return;
    }
    if (retryRef.current)
      void perform(retryRef.current.operation, retryRef.current.caseId, retryRef.current.replyLocale);
  }
  return {
    cases,
    prepareCase,
    composerKey: current ? composerKeys.current.get(current.id) || current.id : '',
    partial: partial && partial.caseId === current?.id ? partial.text : "",
    canStop: Boolean(partial) && partial?.caseId === current?.id,
    stop: () => controller.current?.abort(),
    organize,
    deleteCase,
    current,
    applyServerCase: update,
    fields,
    busy,
    currentBusy: busy && workingCaseId === current?.id,
    error: !current || errorCaseId === current.id ? error : "",
    errorLocale,
    setActiveId,
    drafts,
    changeDraft,
    chooseSuggestion,
    send,
    save,
    confirmAndAnalyze,
    analyze,
    newCase,
    retry,
  };
}
