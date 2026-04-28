export function LoadingState({ msg = "Carregando..." }) {
  return (
    <div style={{ padding: 40, textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
      {msg}
    </div>
  );
}
