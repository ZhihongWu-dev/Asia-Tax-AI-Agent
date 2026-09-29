import { useId, useRef, useState } from "react";
import { MoreHorizontal, Pencil, Archive, ArchiveRestore } from "lucide-react";
import HintButton from "./HintButton";
import { useLocale } from "../locale";

export default function ChatMenu({ title, archived, disabled, onRename, onArchive }: {
  title: string; archived: boolean; disabled: boolean; onRename: () => void; onArchive: () => void;
}) {
  const { locale } = useLocale();
  const en = locale === "en";
  const id = useId(), menu = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ left:0, top:0 });
  const more = en ? "More options" : "更多操作";
  const rename = en ? "Rename" : "重命名";
  const archive = archived ? (en ? "Restore" : "恢复") : (en ? "Archive" : "归档");
  function close(action: () => void) { menu.current?.hidePopover(); action(); }
  return <>
    <HintButton className="history-more icon-button" aria-label={`${more} ${title}`} title={more}
      aria-haspopup="menu" aria-expanded={open} aria-controls={id} disabled={disabled}
      onClick={event => {
        const r = event.currentTarget.getBoundingClientRect();
        setPosition({ left:Math.max(8, Math.min(innerWidth - 192, r.right - 184)), top:Math.max(8, Math.min(innerHeight - 110, r.bottom + 5)) });
        menu.current?.togglePopover();
      }}><MoreHorizontal size={19} /></HintButton>
    <div ref={menu} id={id} popover="auto" role="menu" aria-label={more}
      className="chat-action-menu" style={position}
      onToggle={event => {
        const visible = event.newState === "open";
        setOpen(visible);
        if (visible) menu.current?.querySelector<HTMLButtonElement>("button")?.focus();
      }}
      onKeyDown={event => {
        if (event.key === "Tab") { menu.current?.hidePopover(); return; }
        const items = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>("button") || []);
        const index = items.indexOf(document.activeElement as HTMLButtonElement);
        if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (index + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
          items[next]?.focus();
        }
      }}>
      <button role="menuitem" disabled={disabled} onClick={() => close(onRename)}><Pencil size={16} />{rename}</button>
      <button role="menuitem" disabled={disabled} onClick={() => close(onArchive)}>{archived ? <ArchiveRestore size={16} /> : <Archive size={16} />}{archive}</button>
    </div>
  </>;
}
