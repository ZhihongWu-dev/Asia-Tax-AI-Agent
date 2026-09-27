import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  Globe2,
  Menu,
  PanelRightClose,
  PanelRightOpen,
} from "lucide-react";
import { caseTitle, sourceInfo, type Panel } from "./workspace";
import { useWorkspace } from "./hooks/useWorkspace";
import { isRetryable } from "./api";
import { useLocale } from "./locale";
import { useOverlayFocus } from "./hooks/useOverlayFocus";
import Composer from "./components/Composer";
import Conversation from "./components/Conversation";
import DetailsPanel from "./components/DetailsPanel";
import Sidebar from "./components/Sidebar";
import Welcome, { SuggestedQuestions } from "./components/Welcome";

export default function App() {
  const { t, locale, setLocale } = useLocale();
  const {
    cases,
    current,
    fields,
    busy,
    currentBusy,
    error,
    setActiveId,
    drafts,
    changeDraft,
    send,
    save,
    confirmAndAnalyze,
    analyze,
    newCase: createCase,
    retry,
  } = useWorkspace();
  const [showConsent, setShowConsent] = useState(false);
  const [consent, setConsent] = useState(false);
  const [panel, setPanel] = useState<Panel>(null);
  const [source, setSource] = useState(sourceInfo[0].id);
  const [mobileNav, setMobileNav] = useState(false);
  const [narrow, setNarrow] = useState(
    () => window.matchMedia("(max-width: 1100px)").matches,
  );
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
  useOverlayFocus(panelRef, Boolean(panel), narrow, () => setPanel(null));
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
  function sendMessage(text: string) {
    if (!current.data_approved && !consent) {
      setShowConsent(true);
      return;
    }
    setShowConsent(false);
    void send(text, consent);
  }
  const modalOpen = mobileNav || (narrow && Boolean(panel));
  if (!current)
    return (
      <main className="startup">
        <strong>AsiaTax</strong>
        <p role="status">{t(error ? `error:${error}` : "正在载入工作空间…")}</p>
        {error && (
          <button className="primary-button" onClick={retry}>
            {t("重试")}
          </button>
        )}
      </main>
    );
  return (
    <div className={`app-shell ${panel && !narrow ? "with-panel" : ""}`}>
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
        inert={modalOpen ? true : undefined}
      >
        <header className="topbar">
          <div className="page-title">
            <button
              className="icon-button mobile-menu"
              aria-label={t("打开案例导航")}
              onClick={() => {
                setPanel(null);
                setMobileNav(true);
              }}
            >
              <Menu size={20} />
            </button>
            <span>{empty ? t("税务助手") : caseTitle(current, t)}</span>
          </div>
          <div className="topbar-actions">
            <button
              className="language-toggle"
              aria-label={locale === "zh" ? "Switch to English" : "切换为中文"}
              onClick={() => setLocale(locale === "zh" ? "en" : "zh")}
            >
              <Globe2 size={14} />
              <span>{locale === "zh" ? "EN" : "中文"}</span>
            </button>
            <button
              className="icon-button"
              aria-label={t("法规资料")}
              title={t("法规资料")}
              onClick={() => openPanel("sources")}
            >
              <BookOpen size={18} />
            </button>
            <button
              className="icon-button"
              aria-label={panel ? t("收起案例信息") : t("打开案例信息")}
              title={t("案例信息")}
              aria-expanded={panel === "facts"}
              onClick={() => setPanel(panel ? null : "facts")}
            >
              {panel ? (
                <PanelRightClose size={19} />
              ) : (
                <PanelRightOpen size={19} />
              )}
            </button>
          </div>
        </header>
        <div className="chat-body">
          <div className="workspace-scroll">
            {empty ? (
              <Welcome />
            ) : (
              <Conversation
                current={current}
                fields={fields}
                busy={currentBusy}
                onAnalyze={analyze}
                onFacts={() => openPanel("facts")}
              />
            )}
          </div>
          <div className="composer-area">
            {error && !panel && (
              <div className="request-error" role="alert">
                {t(`error:${error}`)}{" "}
                {isRetryable(error) && (
                  <button onClick={retry}>{t("重试")}</button>
                )}
              </div>
            )}
            {showConsent && (
              <div className="data-consent">
                <label>
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(e) => setConsent(e.target.checked)}
                  />
                  {t("本次仅提交合成研究资料，不含真实客户或个人信息。")}
                </label>
                <p>{t("输入将发送至配置的模型服务。确认后请再次发送。")}</p>
              </div>
            )}

            <Composer
              key={current.id}
              text={drafts[current.id] || ""}
              onChange={changeDraft}
              busy={busy}
              onSend={sendMessage}
            />
            {empty && (
              <SuggestedQuestions
                onSelect={(text) => {
                  changeDraft(text);
                  document
                    .querySelector<HTMLTextAreaElement>("textarea")
                    ?.focus();
                }}
              />
            )}
          </div>
        </div>
        <footer className="workspace-footer">
          {t("专业判断，请由税务顾问复核。")}
        </footer>
      </main>
      {modalOpen && (
        <div
          className="overlay-backdrop"
          aria-hidden="true"
          onClick={() => {
            setMobileNav(false);
            setPanel(null);
          }}
        />
      )}
      {panel && (
        <div
          className="panel-slot"
          ref={panelRef}
          role={narrow ? "dialog" : undefined}
          aria-modal={narrow || undefined}
          aria-label={narrow ? t("研究详情") : undefined}
        >
          <DetailsPanel
            key={`${current.id}-${panel}`}
            panel={panel}
            current={current}
            selectedSource={source}
            onClose={() => setPanel(null)}
            fields={fields}
            busy={busy}
            onConfirm={async () => {
              if (await confirmAndAnalyze()) setPanel(null);
            }}
            error={error}
            onRetry={retry}
            onSave={save}
            onSelectSource={setSource}
          />
        </div>
      )}
    </div>
  );
}
