import type { Attachment } from "./attachments";
import HintButton from "./components/HintButton";
import { useEffect, useRef, useState } from "react";
import { Activity, Globe2, Menu } from "lucide-react";
import { caseTitle, type Panel } from "./workspace";
import { useWorkspace } from "./hooks/useWorkspace";
import { useRun } from "./hooks/useRun";
import { isRetryable } from "./api";
import { languages, nextLocale, useLocale } from "./locale";
import { useOverlayFocus } from "./hooks/useOverlayFocus";
import Composer from "./components/Composer";
import Conversation from "./components/Conversation";
import DetailsPanel from "./components/DetailsPanel";
import RunPanel from "./components/RunPanel";
import Sidebar from "./components/Sidebar";
import Welcome from "./components/Welcome";
import Brand from "./components/Brand";
import BrandLoader from "./components/BrandLoader";
import TaxAtlas from "./components/TaxAtlas";
import ReportPanel from "./components/ReportPanel";

export default function App() {
  const { t, locale, setLocale } = useLocale();
  const nextLanguage = nextLocale(locale);
  const {
    cases,
    current,
    busy,
    currentBusy,
    error,
    setActiveId,
    drafts,
    changeDraft,
    send,
    newCase: createCase,
    retry,
    organize, deleteCase, partial, process, reload, canStop, stop, removeDocument,
  } = useWorkspace();
  const { run, resume, halt } = useRun(current?.id.startsWith("draft-") ? undefined : current?.id, current?.revision, reload);
  const working = run.active || run.turning;
  const started = run.steps.some((step) => step.runs > 0);
  const [runOpen, setRunOpen] = useState(false);
  const wasActive = useRef(false);
  useEffect(() => {
    if (run.active && !wasActive.current) setRunOpen(true);
    wasActive.current = run.active;
  }, [run.active]);
  const [reportOpen, setReportOpen] = useState(false);
  useEffect(() => { setRunOpen(false); setReportOpen(false); }, [current?.id]);
  const [panel, setPanel] = useState<Panel>(null);
  const composerIdentity = useRef({ id: "", key: "" });
  if (current && composerIdentity.current.id !== current.id) {
    const previous = composerIdentity.current;
    composerIdentity.current = { id: current.id, key: previous.id.startsWith("draft-") && busy ? previous.key : current.id };
  }
  const [atlas, setAtlas] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [narrow, setNarrow] = useState(() => window.matchMedia("(max-width: 1100px)").matches);
  const panelRef = useRef<HTMLDivElement>(null),
    navRef = useRef<HTMLDivElement>(null);
  const empty = !current || current.messages.length === 0;
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1100px)");
    const update = () => {
      setNarrow(media.matches);
      if (!media.matches) setMobileNav(false);
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useOverlayFocus(panelRef, Boolean(panel), false, () => setPanel(null));
  useOverlayFocus(navRef, mobileNav, true, () => setMobileNav(false));
  function openPanel(next: Panel) {
    setMobileNav(false);
    setPanel(next);
  }
  function newCase() {
    setPanel(null);
    setMobileNav(false);
    setAtlas(false);
    void createCase();
  }
  function openAtlas() {
    setPanel(null);
    setMobileNav(false);
    setRunOpen(false);
    setAtlas(true);
  }
  const sendMessage = (text: string, files: Attachment[]) => send(text, files);
  if (!current)
    return (
      <main className="startup">
        {error ? <><Brand /><p role="alert">{t(`error:${error}`)}</p></> :
          <BrandLoader fullPage label={t("Loading your workspace…")} />}
        {error && (
          <HintButton className="primary-button" onClick={retry}>
            {t("Retry")}
          </HintButton>
        )}
      </main>
    );
  return (
    <div className={`app-shell ${panel ? "panel-workspace" : ""} ${runOpen && started && !panel && !atlas ? "run-open" : ""}`}>
      <div
        ref={navRef}
        className={`sidebar-slot ${mobileNav ? "is-open" : ""}`}
        role={mobileNav ? "dialog" : undefined}
        aria-modal={mobileNav || undefined}
        aria-label={mobileNav ? t("Chat navigation") : undefined}
        inert={narrow && !mobileNav ? true : undefined}
      >
        <Sidebar
          cases={cases}
          busy={busy}
          onOrganize={organize}
          onDelete={deleteCase}
          activeId={current.id}
          onNew={newCase}
          atlasActive={atlas && !panel}
          onAtlas={openAtlas}
          onClose={() => setMobileNav(false)}
          onPanel={openPanel}
          onSelect={(id) => {
            setActiveId(id);
            setPanel(null);
            setMobileNav(false);
            setAtlas(false);
          }}
        />
      </div>
      {atlas ? (
        <main className="main-workspace atlas-workspace" inert={mobileNav || Boolean(panel) ? true : undefined}>
          <header className="topbar">
            <div className="page-title">
              <HintButton className="icon-button mobile-menu" aria-label={t("Open chat navigation")}
                onClick={() => { setPanel(null); setMobileNav(true); }}>
                <Menu size={20} />
              </HintButton>
              <span>{t("Tax graph")}</span>
            </div>
            <div className="topbar-actions">
              <HintButton className="language-toggle" aria-label={languages[nextLanguage].switchTo}
                onClick={() => setLocale(nextLanguage)}>
                <Globe2 size={14} />
                <span>{languages[nextLanguage].name}</span>
              </HintButton>
            </div>
          </header>
          <TaxAtlas />
        </main>
      ) : <main
        className={`main-workspace ${empty ? "is-empty" : ""}`}
        inert={mobileNav || Boolean(panel) ? true : undefined}
      >
        <header className="topbar">
          <div className="page-title">
            <HintButton
              className="icon-button mobile-menu"
              aria-label={t("Open chat navigation")}
              onClick={() => {
                setPanel(null);
                setMobileNav(true);
              }}
            >
              <Menu size={20} />
            </HintButton>
            <span>{empty ? t("Tax assistant") : caseTitle(current, t)}</span>
          </div>
          <div className="topbar-actions">
            {started && (
              <HintButton
                className={`language-toggle run-toggle ${run.active ? "is-active" : ""}`}
                aria-label={t("Open the progress panel")}
                aria-expanded={runOpen}
                onClick={() => setRunOpen(!runOpen)}
              >
                <Activity size={14} />
                <span>{t("Progress")}</span>
              </HintButton>
            )}
            <HintButton
              className="language-toggle"
              aria-label={languages[nextLanguage].switchTo}
              onClick={() => setLocale(nextLanguage)}
            >
              <Globe2 size={14} />
              <span>{languages[nextLanguage].name}</span>
            </HintButton>
          </div>
        </header>
        <div className="chat-body">
          <div className="workspace-scroll">
            {empty ? (
              <Welcome />
            ) : (
              <Conversation current={current} busy={currentBusy} partial={partial} process={process} blocks={run.blocks} working={working} onRemove={removeDocument}
                onReport={current.id.startsWith("draft-") ? undefined : () => setReportOpen(true)} />
            )}
          </div>
          <div className="composer-area">
            {error && !panel && (
              <div className="request-error" role="alert">
                {t(`error:${error}`)}{" "}
                {isRetryable(error) && <HintButton onClick={retry}>{t("Retry")}</HintButton>}
              </div>
            )}
            <Composer
              key={composerIdentity.current.key}
              lastSentText={current.messages.filter(m => m.role === "user" && !m.delivery).at(-1)?.text}
              text={drafts[current.id] || ""}
              onChange={changeDraft}
              busy={busy || working}
              onStop={canStop ? stop : undefined}
              onSend={sendMessage}
            />
          </div>
        </div>
        <footer className="workspace-footer">
          {t("Professional judgments require adviser review.")}
        </footer>
      </main>}
      {mobileNav && (
        <div
          className="overlay-backdrop"
          aria-hidden="true"
          onClick={() => {
            setMobileNav(false);
            setPanel(null);
          }}
        />
      )}
      {runOpen && started && !panel && !atlas && (
        <div className="run-slot">
          <RunPanel caseId={current?.id} run={run} onResume={() => void resume()} onHalt={() => void halt()} onClose={() => setRunOpen(false)}
            onReport={() => setReportOpen(true)} />
        </div>
      )}
      {reportOpen && !current.id.startsWith("draft-") && <ReportPanel caseId={current.id} onClose={() => setReportOpen(false)} />}
      {panel && (
        <div className="panel-slot" ref={panelRef} role="main" aria-label={t("About Taxrora")}>
          <DetailsPanel key={panel} onClose={() => setPanel(null)} />
        </div>
      )}
    </div>
  );
}
