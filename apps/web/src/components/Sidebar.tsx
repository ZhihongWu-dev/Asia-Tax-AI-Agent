import {
  BookOpen,
  CircleHelp,
  MessageSquare,
  Plus,
  Scale,
  Search,
  X,
} from "lucide-react";
import { useState } from "react";
import { caseTitle, type Case, type Panel } from "../workspace";
import { useLocale } from "../locale";

export default function Sidebar({
  cases,
  activeId,
  onSelect,
  onNew,
  onPanel,
  onClose,
}: {
  cases: Case[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onPanel: (panel: Panel) => void;
  onClose: () => void;
}) {
  const { t } = useLocale();
  const [query, setQuery] = useState("");
  const visible = cases.filter((c) =>
    caseTitle(c, t).toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <aside className="sidebar" aria-label={t("案例导航")}>
      <div className="brand">
        <span className="brand-mark">
          <Scale size={23} strokeWidth={1.5} />
        </span>
        <span>AsiaTax</span>
        <button
          className="icon-button mobile-close"
          onClick={onClose}
          aria-label={t("关闭案例导航")}
        >
          <X size={18} />
        </button>
      </div>
      <button
        className="new-case"
        onClick={() => {
          setQuery("");
          onNew();
        }}
      >
        <Plus size={17} />
        {t("新对话")}
      </button>
      <label className="case-search">
        <Search size={15} />
        <input
          aria-label={t("搜索对话")}
          placeholder={t("搜索对话")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <div className="nav-heading">{t("最近对话")}</div>
      <nav className="case-list" aria-label={t("研究案例")}>
        {visible.map((c) => (
          <button
            key={c.id}
            className={`case-item ${activeId === c.id ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
            aria-current={activeId === c.id ? "page" : undefined}
          >
            <MessageSquare size={15} />
            <span>{caseTitle(c, t)}</span>
          </button>
        ))}
        {!visible.length && (
          <p className="no-results">{t("没有找到匹配的案例")}</p>
        )}
      </nav>
      <div className="sidebar-bottom">
        <button className="side-link" onClick={() => onPanel("sources")}>
          <BookOpen size={17} />
          {t("法规资料库")}
        </button>
        <button className="side-link" onClick={() => onPanel("about")}>
          <CircleHelp size={17} />
          {t("关于 AsiaTax")}
        </button>
      </div>
    </aside>
  );
}
