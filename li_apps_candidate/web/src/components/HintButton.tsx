import { useId, useRef, useState, type ButtonHTMLAttributes } from "react";
import { createPortal } from "react-dom";

/** Identical pointer and keyboard hints, outside clipping scroll containers. */
export default function HintButton({ title, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState<{ x: number; y: number; below: boolean } | null>(null);
  const label = title || props["aria-label"];
  function show() {
    if (!button.current || props.disabled || !label) return;
    const rect = button.current.getBoundingClientRect();
    setPosition({ x: Math.max(100, Math.min(innerWidth - 100, rect.left + rect.width / 2)),
      y: rect.top < 48 ? rect.bottom + 8 : rect.top - 8, below: rect.top < 48 });
  }
  return <>
    <button {...props} ref={button} aria-describedby={position ? id : undefined}
      onMouseEnter={event => { show(); props.onMouseEnter?.(event); }}
      onMouseLeave={event => { setPosition(null); props.onMouseLeave?.(event); }}
      onFocus={event => { show(); props.onFocus?.(event); }}
      onBlur={event => { setPosition(null); props.onBlur?.(event); }}
      onClick={event => { setPosition(null); props.onClick?.(event); }}
      onKeyDown={event => { if (event.key === "Escape") setPosition(null); props.onKeyDown?.(event); }}>
      {children}
    </button>
    {position && createPortal(<span id={id} role="tooltip" className="action-tooltip" style={{ left:position.x, top:position.y, transform:position.below ? "translateX(-50%)" : "translate(-50%, -100%)" }}>{label}</span>, document.body)}
  </>;
}
