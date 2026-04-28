export function Badge({ text, color, bg }) {
  return (
    <span style={{
      padding: "2px 9px", borderRadius: 4, fontSize: 10, fontWeight: 600,
      fontFamily: "var(--mono)", color, background: bg,
      border: `1px solid ${color}25`, letterSpacing: 0.5,
    }}>
      {text}
    </span>
  );
}
