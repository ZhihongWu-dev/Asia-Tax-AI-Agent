import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useLocale } from "../locale";

// A list of attachments shown as a small scrolling window; the arrow below opens it to its full length. The count and the
// arrow appear only once the files no longer fit, so one or two files look as before.
export default function FileWindow({ count, listClass, children }: { count: number; listClass: string; children: ReactNode }) {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const [over, setOver] = useState(false);
  const list = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = list.current;
    if (!el) return;
    const check = () => setOver(el.scrollHeight > el.clientHeight + 1);
    check();
    const watch = new ResizeObserver(check);
    watch.observe(el);
    return () => watch.disconnect();
  }, [count, open]);
  const toggle = open || over;
  return (
    <div className={`file-window ${open ? "open" : ""}`}>
      {toggle && <div className="file-window-head">{t("Attachments")} {count}</div>}
      <div ref={list} className={`file-window-list ${listClass}`}>{children}</div>
      {toggle && (
        <button type="button" className="file-window-toggle" onClick={() => setOpen(!open)} aria-expanded={open}
          aria-label={t(open ? "Collapse" : "Show all")} title={t(open ? "Collapse" : "Show all")}>
          {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
      )}
    </div>
  );
}
