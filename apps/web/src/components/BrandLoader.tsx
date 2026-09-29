import { BrandMark } from "./Brand";
import "./BrandLoader.css";

/** One motion signature for startup and in-conversation waiting. */
export default function BrandLoader({ label, fullPage = false }: {
  label: string;
  fullPage?: boolean;
}) {
  return (
    <div className={`brand-loader ${fullPage ? "brand-loader-page" : "brand-loader-inline"}`}
      role="status" aria-live="polite" aria-label={label}>
      <span className="brand-loader-emblem" aria-hidden="true">
        <span className="brand-loader-halo" />
        <span className="brand-loader-orbit" />
        <BrandMark size={fullPage ? 64 : 28} />
      </span>
      {fullPage && <span className="brand-loader-wordmark" aria-hidden="true"><strong>Tax</strong>ora</span>}
    </div>
  );
}
