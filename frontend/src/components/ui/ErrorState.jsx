export function ErrorState({ msg }) {
  return (
    <div style={{
      padding: 20, color: "var(--danger)", fontSize: 12,
      background: "var(--danger)08", borderRadius: 8,
      border: "1px solid var(--danger)20",
    }}>
      Erro: {msg}
    </div>
  );
}
