/** Original Taxora T mark, approved in the September 28 brand concept. */
export function BrandMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="currentColor" aria-hidden="true" focusable="false">
      <rect x="4" y="6" width="40" height="7" rx="0.8" />
      <rect x="20" y="12" width="8" height="29" rx="0.8" />
      <rect x="9" y="18" width="8" height="5" rx="0.8" />
      <rect x="31" y="18" width="8" height="5" rx="0.8" />
    </svg>
  );
}

export default function Brand() {
  return (
    <span className="brand-lockup" role="img" aria-label="Taxora">
      <BrandMark />
      <span className="brand-wordmark" aria-hidden="true"><strong>Tax</strong>ora</span>
    </span>
  );
}
