import { withAttachments, type Attachment } from "../attachments";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { addItem, type ActivityItem, type Case, type Message } from "../workspace";

export function useWorkspace() {
  const [cases, setCases] = useState<Case[]>([]);
  const [activeId, setActiveId] = useState(location.hash.slice(1));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [errorCaseId, setErrorCaseId] = useState("");
  const locked = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const [partial, setPartial] = useState<{ caseId: string; text: string } | null>(null);
  const [process, setProcess] = useState<{ caseId: string; items: ActivityItem[] } | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const retryRef = useRef<{ operation: () => Promise<void>; caseId: string } | null>(null);
  const [workingCaseId, setWorkingCaseId] = useState("");
  const [outbox, setOutbox] = useState<{ caseId: string; message: Message }[]>([]);
  const boot = useRef<Promise<Case[]> | null>(null);
  const storedCurrent = cases.find((c) => c.id === activeId) || cases[0];
  const localMessages = outbox
    .filter((item) => item.caseId === storedCurrent?.id)
    .map((item) => item.message);
  const current =
    storedCurrent && localMessages.length
      ? { ...storedCurrent, messages: [...storedCurrent.messages, ...localMessages] }
      : storedCurrent;
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  async function initialize() {
    const list = await api.list();
    return list.length ? list : [await api.create()];
  }
  useEffect(() => {
    let live = true;
    boot.current ||= initialize();
    boot.current
      .then((data) => {
        if (live) setCases(data);
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
  async function perform(operation: () => Promise<void>, caseId = current?.id || "") {
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
  function send(text: string, files: Attachment[] = []) {
    const messageText = withAttachments(text, files);
    let completed = false;
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
              item.message.text === messageText
            ),
        ),
        { caseId: doc.id, message: { id: localId, role: "user", text: messageText, delivery: "sending" } },
      ]);
      setDrafts((all) => (all[doc.id]?.trim() === text ? { ...all, [doc.id]: "" } : all));
      try {
        const abort = new AbortController();
        controller.current = abort;
        setPartial({ caseId: doc.id, text: "" });
        setProcess({ caseId: doc.id, items: [] });
        const next = await api.stream(doc, messageText, requestId, abort.signal, (chunk, reset) =>
          setPartial((previous) =>
            previous?.caseId === doc.id ? { ...previous, text: reset ? "" : previous.text + chunk } : previous,
          ), (item) =>
          setProcess((previous) =>
            previous?.caseId === doc.id ? { ...previous, items: addItem(previous.items, item) } : previous,
          ));
        update(next);
        completed = true;
        setOutbox((all) => all.filter((item) => item.message.id !== localId));
      } catch (e) {
        if (e instanceof ApiError && e.code === "revision_conflict") update(await api.get(doc.id));
        if (controller.current?.signal.aborted) {
          setOutbox((all) => all.filter((item) => item.message.id !== localId));
          setDrafts((all) => (all[doc.id] ? all : { ...all, [doc.id]: text }));
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
        setProcess(null);
      }
    }, doc.id).then((success) => success && completed);
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
  function organize(id: string, changes: { title?: string; archived?: boolean }) {
    const doc = cases.find((c) => c.id === id);
    if (!doc) return Promise.resolve(false);
    return perform(async () => {
      try {
        update(await api.organize(doc, changes));
      } catch (e) {
        if (e instanceof ApiError && e.code === "revision_conflict") update(await api.get(doc.id));
        throw e;
      }
    }, id);
  }
  function reload(id: string) {
    api.get(id).then(update).catch(() => {});
  }
  function retry() {
    if (!current) {
      boot.current = null;
      location.reload();
      return;
    }
    if (retryRef.current) void perform(retryRef.current.operation, retryRef.current.caseId);
  }
  return {
    cases,
    partial: partial && partial.caseId === current?.id ? partial.text : "",
    process: process && process.caseId === current?.id ? process.items : [],
    reload,
    canStop: Boolean(partial) && partial?.caseId === current?.id,
    stop: () => controller.current?.abort(),
    organize,
    current,
    busy,
    currentBusy: busy && workingCaseId === current?.id,
    error: !current || errorCaseId === current.id ? error : "",
    setActiveId,
    drafts,
    changeDraft,
    send,
    newCase,
    retry,
  };
}
