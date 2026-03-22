export default function ScanlineOverlay() {
  return (
    <div
      className="scanline-overlay"
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'repeating-linear-gradient(0deg, rgba(0,255,65,0.03) 0px, rgba(0,255,65,0.03) 1px, transparent 1px, transparent 2px)',
        pointerEvents: 'none',
        zIndex: 9999,
      }}
    />
  );
}
