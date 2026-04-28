export function MetricBox({ label, value, unit, color = "var(--accent)" }) {
  return (
    <div style={{
      padding: "14px 16px", background: "var(--surface)", borderRadius: 8,
      border: "1px solid var(--border)", flex: 1, minWidth: 110,
    }}>
      <div style={{
        fontSize: 10, color: "var(--muted)", marginBottom: 6,
        letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 500,
      }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--mono)", color, lineHeight: 1 }}>
        {value}
        <span style={{ fontSize: 10, fontWeight: 400, color: "var(--muted)", marginLeft: 3 }}>{unit}</span>
      </div>
    </div>
  );
}
