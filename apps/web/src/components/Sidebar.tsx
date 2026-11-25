import HintButton from "./HintButton";
import {
  ChevronRight,
  CircleHelp,
  Map as MapIcon,
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
  onDelete,
  busy,
  atlasActive,
  onAtlas,
}: {
  cases: Case[];
  atlasActive: boolean;
  onAtlas: () => void;
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onPanel: (panel: Panel) => void;
  onClose: () => void;
  onOrganize: (id: string, changes: { title?: string; archived?: boolean }) => Promise<boolean>;
  onDelete: (id: string) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useLocale();
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [query, setQuery] = useState("");
  const [archived, setArchived] = useState(false);
  const [editing, setEditing] = useState("");
  const [title, setTitle] = useState("");
  const [actionError, setActionError] = useState(false);
  const visible = cases.filter((c) =>
    c.messages.length > 0 && Boolean(c.archived) === archived && caseTitle(c, t).toLowerCase().includes(query.toLowerCase()),
  ).sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  const groups = [t("Today"), t("Yesterday"), t("Earlier")];
  const group = (c: Case) => {
    const time = new Date(c.updated_at || c.created_at || "").getTime();
    return time >= today.getTime() ? 0 : time >= yesterday.getTime() ? 1 : 2;
  };
  return (
    <aside className="sidebar" aria-label={t("Chat navigation")}>
      <div className="brand">
        <Brand />
        <HintButton
          className="icon-button mobile-close"
          onClick={onClose}
          aria-label={t("Close chat navigation")}
        >
          <X size={18} />
        </HintButton>
      </div>
      <button className={`atlas-entry ${atlasActive ? "active" : ""}`} aria-pressed={atlasActive} onClick={onAtlas}>
        <span className="atlas-entry-icon"><MapIcon size={16} /></span>
        <span className="atlas-entry-text">
          <strong>{t("Tax graph")}</strong>
          <small>{t("Dividend tax by jurisdiction, glossary")}</small>
        </span>
        <ChevronRight size={16} style={{ marginLeft: "auto", flexShrink: 0 }} />
      </button>
      <HintButton
        className="new-case"
        disabled={busy}
        onClick={() => {
          setQuery("");
          onNew();
        }}
      >
        <Plus size={17} />
        {t("New chat")}
      </HintButton>
      <label className="case-search">
        <Search size={15} />
        <input
          aria-label={t("Search chats")}
          placeholder={t("Search chats")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <div className="history-tabs"><HintButton aria-pressed={!archived} onClick={() => setArchived(false)}>{t("Recent chats")}</HintButton><HintButton aria-pressed={archived} onClick={() => setArchived(true)}>{t("Archived")}</HintButton></div>
      {actionError && <p role="alert">{t("Could not update. Refresh and retry.")}</p>}
      <nav className="case-list" aria-label={t("Research cases")}>
        {visible.map((c, index) => (
          <div className="history-entry" key={c.id}>
          {(index === 0 || group(c) !== group(visible[index - 1])) && <div className="nav-heading">{groups[group(c)]}</div>}
          {editing === c.id ? <form className="rename-form" onSubmit={async event => {
            event.preventDefault(); setActionError(false);
            if (await onOrganize(c.id, { title: title.trim() })) setEditing(""); else setActionError(true);
          }}><input autoFocus maxLength={100} aria-label={t("Chat title")} value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => { if (e.key === "Escape") setEditing(""); }} />
            <HintButton disabled={busy || !title.trim()}>{t("Save")}</HintButton><HintButton type="button" disabled={busy} onClick={() => setEditing("")}>{t("Cancel")}</HintButton></form> : <div className={`history-row ${activeId === c.id ? "is-active" : ""}`}>
          <HintButton
            key={c.id}
            className={`case-item ${activeId === c.id && !atlasActive ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
            aria-current={activeId === c.id && !atlasActive ? "page" : undefined}
          >
            <MessageSquare size={15} />
            <span>{caseTitle(c, t)}</span>
          </HintButton>
          <ChatMenu title={caseTitle(c, t)} archived={archived} disabled={busy}
            onRename={() => { setEditing(c.id); setTitle(caseTitle(c, t)); }}
            onDelete={async () => {
              if (!window.confirm(t("Delete this conversation and its case files, attachments and reports? This cannot be undone."))) return;
              setActionError(false);
              if (!await onDelete(c.id)) setActionError(true);
            }}
            onArchive={async () => {
              setActionError(false);
              if (!await onOrganize(c.id, { archived: !archived })) setActionError(true);
            }} />
          </div>}
          </div>
        ))}
        {!visible.length && (
          <p className="no-results">{t("No matching chats")}</p>
        )}
      </nav>
      <div className="sidebar-bottom">
        {user && <div className="account-row"><UserRound size={17} /><span title={user.email}>{user.email}</span><HintButton className="icon-button" disabled={signingOut} aria-label={t("Sign out")} title={t("Sign out")} onClick={async () => { setSigningOut(true); setLogoutError(false); try { await logout(); } catch { setLogoutError(true); } finally { setSigningOut(false); } }}><LogOut size={17} /></HintButton></div>}
        {logoutError && <p role="alert">{t("Could not sign out. Please retry.")}</p>}
        <HintButton className="side-link" onClick={() => onPanel("about")}>
          <CircleHelp size={17} />
          {t("About Taxrora")}
        </HintButton>
      </div>
    </aside>
  );
}
