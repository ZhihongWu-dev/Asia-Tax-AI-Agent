import {
  BookOpen,
  ChevronRight,
  CircleHelp,
  MessageSquare,
  Plus,
  Scale,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { useState } from "react";
import type { Case, Panel } from "../demo";

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
  const [query, setQuery] = useState("");
  const visible = cases.filter((c) =>
    c.title.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <aside className="sidebar" aria-label="案例导航">
      <div className="brand">
        <span className="brand-mark">
          <Scale size={24} strokeWidth={1.5} />
        </span>
        <div>
          AsiaTax<span className="brand-sub">RESEARCH WORKSPACE</span>
        </div>
        <button
          className="icon-button mobile-close"
          onClick={onClose}
          aria-label="关闭案例导航"
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
        <Plus size={18} />
        新建研究案例<span>＋</span>
      </button>
      <label className="case-search">
        <Search size={15} />
        <input
          aria-label="搜索案例"
          placeholder="搜索案例"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <div className="nav-heading">
        工作空间<span>{cases.length.toString().padStart(2, "0")}</span>
      </div>
      <nav className="case-list" aria-label="研究案例">
        {visible.map((c) => (
          <button
            key={c.id}
            className={`case-item ${activeId === c.id ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
            aria-current={activeId === c.id ? "page" : undefined}
          >
            <MessageSquare size={16} />
            <span>
              {c.title}
              <small>
                {c.stage === "empty"
                  ? "等待开始"
                  : c.stage === "review"
                    ? "研究清单 · 示例"
                    : "待补充事实"}
              </small>
            </span>
            {activeId === c.id && <span className="active-dot" />}
          </button>
        ))}
        {visible.length === 0 && (
          <p className="no-results">没有找到匹配的案例</p>
        )}
      </nav>
      <div className="sidebar-bottom">
        <button className="side-link" onClick={() => onPanel("sources")}>
          <BookOpen size={17} />
          法规资料库
          <ChevronRight size={14} />
        </button>
        <button className="side-link" onClick={() => onPanel("about")}>
          <CircleHelp size={17} />
          使用说明
          <ChevronRight size={14} />
        </button>
        <div className="research-note">
          <ShieldCheck size={17} />
          <div>
            让每一步研究，有据可循<p>L0 内部研究 · 香港 FSIE</p>
          </div>
        </div>
        <div className="workspace-user">
          <span className="user-avatar">研</span>
          <div>
            个人研究空间<small>本次会话 · 内存保存</small>
          </div>
          <span className="workspace-badge">L0</span>
        </div>
      </div>
    </aside>
  );
}
