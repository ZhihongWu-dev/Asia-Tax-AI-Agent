import type { Attachment } from "./attachments";
import HintButton from "./components/HintButton";
import { useEffect, useRef, useState } from "react";
import { Activity, Globe2, Menu } from "lucide-react";
import { caseTitle, type Panel } from "./workspace";
import { useWorkspace } from "./hooks/useWorkspace";
import { useRun } from "./hooks/useRun";
import { isRetryable } from "./api";
import { useLocale } from "./locale";
import { useOverlayFocus } from "./hooks/useOverlayFocus";
import Composer from "./components/Composer";
import Conversation from "./components/Conversation";
import DetailsPanel from "./components/DetailsPanel";
import RunPanel from "./components/RunPanel";
import Sidebar from "./components/Sidebar";
import Welcome from "./components/Welcome";
import Brand from "./components/Brand";
import BrandLoader from "./components/BrandLoader";

export default function App() {
  const { t, locale, setLocale } = useLocale();
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
    organize, partial, process, reload, canStop, stop,
  } = useWorkspace();
  const { run, resume, halt } = useRun(current?.id, current?.revision, reload);
  const working = run.active || run.turning;
  const started = run.steps.some((step) => step.runs > 0);
  const [runOpen, setRunOpen] = useState(false);
  const wasActive = useRef(false);
  useEffect(() => {
    if (run.active && !wasActive.current) setRunOpen(true);
    wasActive.current = run.active;
  }, [run.active]);
  useEffect(() => setRunOpen(false), [current?.id]);
  const [panel, setPanel] = useState<Panel>(null);
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
    void createCase();
  }
  const sendMessage = (text: string, files: Attachment[]) => send(text, files);
  if (!current)
    return (
      <main className="startup">
        {error ? <><Brand /><p role="alert">{t(`error:${error}`)}</p></> :
          <BrandLoader fullPage label={t("正在载入工作空间…")} />}
        {error && (
          <HintButton className="primary-button" onClick={retry}>
            {t("重试")}
          </HintButton>
        )}
      </main>
    );
  return (
    <div className={`app-shell ${panel ? "panel-workspace" : ""} ${runOpen && started && !panel ? "run-open" : ""}`}>
      <div
        ref={navRef}
        className={`sidebar-slot ${mobileNav ? "is-open" : ""}`}
        role={mobileNav ? "dialog" : undefined}
        aria-modal={mobileNav || undefined}
        aria-label={mobileNav ? t("案例导航") : undefined}
        inert={narrow && !mobileNav ? true : undefined}
      >
        <Sidebar
          cases={cases}
          busy={busy}
          onOrganize={organize}
          activeId={current.id}
          onNew={newCase}
          onClose={() => setMobileNav(false)}
          onPanel={openPanel}
          onSelect={(id) => {
            setActiveId(id);
            setPanel(null);
            setMobileNav(false);
          }}
        />
      </div>
      <main
        className={`main-workspace ${empty ? "is-empty" : ""}`}
        inert={mobileNav || Boolean(panel) ? true : undefined}
      >
        <header className="topbar">
          <div className="page-title">
            <HintButton
              className="icon-button mobile-menu"
              aria-label={t("打开案例导航")}
              onClick={() => {
                setPanel(null);
                setMobileNav(true);
              }}
            >
              <Menu size={20} />
            </HintButton>
            <span>{empty ? t("税务助手") : caseTitle(current, t)}</span>
          </div>
          <div className="topbar-actions">
            {started && (
              <HintButton
                className={`language-toggle run-toggle ${run.active ? "is-active" : ""}`}
                aria-label={t("打开进度面板")}
                aria-expanded={runOpen}
                onClick={() => setRunOpen(!runOpen)}
              >
                <Activity size={14} />
                <span>{t("进度")}</span>
              </HintButton>
            )}
            <HintButton
              className="language-toggle"
              aria-label={locale === "zh" ? "Switch to English" : "切换为中文"}
              onClick={() => setLocale(locale === "zh" ? "en" : "zh")}
            >
              <Globe2 size={14} />
              <span>{locale === "zh" ? "EN" : "中文"}</span>
            </HintButton>
          </div>
        </header>
        <div className="chat-body">
          <div className="workspace-scroll">
            {empty ? (
              <Welcome />
            ) : (
              <Conversation current={current} busy={currentBusy} partial={partial} process={process} blocks={run.blocks} working={working} />
            )}
          </div>
          <div className="composer-area">
            {error && !panel && (
              <div className="request-error" role="alert">
                {t(`error:${error}`)}{" "}
                {isRetryable(error) && <HintButton onClick={retry}>{t("重试")}</HintButton>}
              </div>
            )}
            <Composer
              key={current.id}
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
          {t("专业判断，请由税务顾问复核。")}
        </footer>
      </main>
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
      {runOpen && started && !panel && (
        <div className="run-slot">
          <RunPanel run={run} onResume={() => void resume()} onHalt={() => void halt()} onClose={() => setRunOpen(false)} />
        </div>
      )}
      {panel && (
        <div className="panel-slot" ref={panelRef} role="main" aria-label={t("关于 Taxrora")}>
          <DetailsPanel key={panel} onClose={() => setPanel(null)} />
        </div>
      )}
    </div>
  );
}
