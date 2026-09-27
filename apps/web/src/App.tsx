import { useLocale } from "./locale";
import { useEffect, useRef, useState, type RefObject } from "react";
import {
  BookOpen,
  ChevronRight,
  FileText,
  Globe2,
  Menu,
  PanelRightClose,
  PanelRightOpen,
  ShieldCheck,
} from "lucide-react";
import {
  makeCase,
  caseTitle,
  factValue,
  message,
  sourceInfo,
  submitText,
  type Case,
  type Facts,
  type Panel,
} from "./demo";
import Composer from "./components/Composer";
import Conversation from "./components/Conversation";
import DetailsPanel from "./components/DetailsPanel";
import Sidebar from "./components/Sidebar";
import Welcome from "./components/Welcome";

function useOverlayFocus(
  ref: RefObject<HTMLDivElement | null>,
  open: boolean,
  modal: boolean,
  close: () => void,
) {
  const closeRef = useRef(close);
  closeRef.current = close;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const root = ref.current;
    const focusable = () => [
      ...(root?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href], input, textarea, select, [tabindex="0"]',
      ) ?? []),
    ];
    focusable()[0]?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeRef.current();
      }
      if (modal && e.key === "Tab") {
        const elements = focusable(),
          first = elements[0],
          last = elements.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, modal, ref]);
}

export default function App() {
  const { t, locale, setLocale } = useLocale();
  const [cases, setCases] = useState<Case[]>(() => [makeCase()]);
  const [activeId, setActiveId] = useState("");
  const current = cases.find((c) => c.id === activeId) || cases[0];
  const [panel, setPanel] = useState<Panel>(null);
  const [source, setSource] = useState(sourceInfo[0].id);
  const [starter, setStarter] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [narrow, setNarrow] = useState(
    () => window.matchMedia("(max-width: 1100px)").matches,
  );
  const panelRef = useRef<HTMLDivElement>(null),
    navRef = useRef<HTMLDivElement>(null);
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
  function updateCase(updater: (c: Case) => Case) {
    setCases((all) => all.map((c) => (c.id === current.id ? updater(c) : c)));
  }
  function openPanel(next: Panel) {
    setMobileNav(false);
    setPanel(next);
  }
  function newCase() {
    const next = makeCase();
    setCases((all) => [next, ...all]);
    setActiveId(next.id);
    setStarter("");
    setPanel(null);
    setMobileNav(false);
  }
  function saveFacts(facts: Facts) {
    updateCase((c) => ({
      ...c,
      facts,
      confirmed: false,
      stage: "facts",
      messages: [
        ...c.messages,
        message(
          "assistant",
          "案例事实已更新。之前的研究清单已撤回，请核对最新信息后重新确认。",
        ),
      ],
    }));
    setPanel(null);
  }
  function confirmFacts() {
    updateCase((c) => ({ ...c, confirmed: true, stage: "receipt" }));
  }
  function chooseReceipt(value: string) {
    updateCase((c) => ({
      ...c,
      facts: { ...c.facts, receipt: value },
      stage: "review",
      messages: [
        ...c.messages,
        message("user", `${t("收取情况")}: ${t(value)}`),
      ],
    }));
  }
  const modalOpen = mobileNav || (narrow && Boolean(panel));
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
            setStarter("");
            setPanel(null);
            setMobileNav(false);
          }}
        />
      </div>
      <main className="main-workspace" inert={modalOpen ? true : undefined}>
        <header className="topbar">
          <div className="breadcrumb">
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
            <span className="breadcrumb-root">{t("研究空间")}</span>
            <ChevronRight size={13} />
            <strong>{caseTitle(current, t)}</strong>
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
            <span className="preview-badge">
              <span />
              {t("交互预览")}
            </span>
            <button
              className="icon-button"
              aria-label={panel ? t("收起案例信息") : t("打开案例信息")}
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
        <div className="contextbar">
          <div>
            <span className="context-region">
              <Globe2 size={14} />
              {t("中国香港")}
            </span>
            <span className="context-divider" />
            <span>{t("FSIE 境外收入研究")}</span>
          </div>
          <button onClick={() => openPanel("sources")}>
            <BookOpen size={14} />
            <span>{t("法规资料")}</span>
            <ChevronRight size={12} />
          </button>
        </div>
        <div className="workspace-scroll">
          {current.stage === "empty" ? (
            <Welcome
              onStarter={(text) => {
                setStarter(text);
                document
                  .querySelector<HTMLTextAreaElement>("textarea")
                  ?.focus();
              }}
            />
          ) : (
            <Conversation
              current={current}
              onPanel={openPanel}
              onConfirm={confirmFacts}
              onReceipt={chooseReceipt}
              onSource={(id) => {
                setSource(id);
                openPanel("sources");
              }}
            />
          )}
        </div>
        <div
          className={`composer-area ${current.stage === "empty" ? "welcome-composer" : ""}`}
        >
          {current.stage !== "empty" && (
            <div className="case-context">
              <span>
                <FileText size={13} />
                {factValue(current, "income", t) || t("收入类型待确认")}
              </span>
              <button onClick={() => openPanel("facts")}>
                {t("查看案例信息")}
                <ChevronRight size={12} />
              </button>
            </div>
          )}
          <Composer
            key={current.id}
            starter={starter}
            onClearStarter={() => setStarter("")}
            onSend={(text) => updateCase((c) => submitText(c, text))}
          />
        </div>
        <footer className="workspace-footer">
          <span>
            <ShieldCheck size={12} />
            {t("研究辅助，不构成正式税务意见")}
          </span>
          <span>ASIATAX / L0</span>
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
            onSave={saveFacts}
            onSelectSource={setSource}
          />
        </div>
      )}
    </div>
  );
}
