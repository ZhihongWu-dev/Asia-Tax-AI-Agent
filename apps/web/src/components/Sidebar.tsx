import HintButton from "./HintButton";
import {
  BookOpen,
  CircleHelp,
  MessageSquare,
  Plus,
  Search,
  X,
} from "lucide-react";
import { useState } from "react";
import { caseTitle, type Case, type Panel } from "../workspace";
import { useLocale } from "../locale";
import Brand from "./Brand";
import { useAuth } from "../auth";
import { LogOut, UserRound } from "lucide-react";
import ChatMenu from "./ChatMenu";

export default function Sidebar({
  cases,
  activeId,
  onSelect,
  onNew,
  onPanel,
  onClose,
  onOrganize,
  busy,
}: {
  cases: Case[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onPanel: (panel: Panel) => void;
  onClose: () => void;
  onOrganize: (id: string, changes: { title?: string; archived?: boolean }) => Promise<boolean>;
  busy: boolean;
}) {
  const { t, locale } = useLocale();
  const say = (zh: string, en: string) => locale === "en" ? en : zh;
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [query, setQuery] = useState("");
  const [archived, setArchived] = useState(false);
  const [editing, setEditing] = useState("");
  const [title, setTitle] = useState("");
  const [actionError, setActionError] = useState(false);
  const visible = cases.filter((c) =>
    Boolean(c.archived) === archived && caseTitle(c, t).toLowerCase().includes(query.toLowerCase()),
  ).sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  const groups = [say("今天", "Today"), say("昨天", "Yesterday"), say("更早", "Earlier")];
  const group = (c: Case) => {
    const time = new Date(c.updated_at || c.created_at || "").getTime();
    return time >= today.getTime() ? 0 : time >= yesterday.getTime() ? 1 : 2;
  };
  return (
    <aside className="sidebar" aria-label={t("案例导航")}>
      <div className="brand">
        <Brand />
        <HintButton
          className="icon-button mobile-close"
          onClick={onClose}
          aria-label={t("关闭案例导航")}
        >
          <X size={18} />
        </HintButton>
      </div>
      <HintButton
        className="new-case"
        disabled={busy}
        onClick={() => {
          setQuery("");
          onNew();
        }}
      >
        <Plus size={17} />
        {t("新对话")}
      </HintButton>
      <label className="case-search">
        <Search size={15} />
        <input
          aria-label={t("搜索对话")}
          placeholder={t("搜索对话")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <div className="history-tabs"><HintButton aria-pressed={!archived} onClick={() => setArchived(false)}>{t("最近对话")}</HintButton><HintButton aria-pressed={archived} onClick={() => setArchived(true)}>{say("已归档", "Archived")}</HintButton></div>
      {actionError && <p role="alert">{say("操作失败，请刷新后重试。", "Could not update. Refresh and retry.")}</p>}
      <nav className="case-list" aria-label={t("研究案例")}>
        {visible.map((c, index) => (
          <div className="history-entry" key={c.id}>
          {(index === 0 || group(c) !== group(visible[index - 1])) && <div className="nav-heading">{groups[group(c)]}</div>}
          {editing === c.id ? <form className="rename-form" onSubmit={async event => {
            event.preventDefault(); setActionError(false);
            if (await onOrganize(c.id, { title: title.trim() })) setEditing(""); else setActionError(true);
          }}><input autoFocus maxLength={100} aria-label={say("对话名称", "Chat title")} value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => { if (e.key === "Escape") setEditing(""); }} />
            <HintButton disabled={busy || !title.trim()}>{say("保存", "Save")}</HintButton><HintButton type="button" disabled={busy} onClick={() => setEditing("")}>{say("取消", "Cancel")}</HintButton></form> : <div className={`history-row ${activeId === c.id ? "is-active" : ""}`}>
          <HintButton
            key={c.id}
            className={`case-item ${activeId === c.id ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
            aria-current={activeId === c.id ? "page" : undefined}
          >
            <MessageSquare size={15} />
            <span>{caseTitle(c, t)}</span>
          </HintButton>
          <ChatMenu title={caseTitle(c, t)} archived={archived} disabled={busy}
            onRename={() => { setEditing(c.id); setTitle(caseTitle(c, t)); }}
            onArchive={async () => {
              setActionError(false);
              if (!await onOrganize(c.id, { archived: !archived })) setActionError(true);
            }} />
          </div>}
          </div>
        ))}
        {!visible.length && (
          <p className="no-results">{t("没有找到匹配的案例")}</p>
        )}
      </nav>
      <div className="sidebar-bottom">
        {user && <div className="account-row"><UserRound size={17} /><span title={user.email}>{user.email}</span><HintButton className="icon-button" disabled={signingOut} aria-label={t("退出登录")} title={t("退出登录")} onClick={async () => { setSigningOut(true); setLogoutError(false); try { await logout(); } catch { setLogoutError(true); } finally { setSigningOut(false); } }}><LogOut size={17} /></HintButton></div>}
        {logoutError && <p role="alert">{t("退出失败，请重试。")}</p>}
        <HintButton className="side-link" onClick={() => onPanel("sources")}>
          <BookOpen size={17} />
          {t("法规资料库")}
        </HintButton>
        <HintButton className="side-link" onClick={() => onPanel("about")}>
          <CircleHelp size={17} />
          {t("关于 Taxora")}
        </HintButton>
      </div>
    </aside>
  );
}
