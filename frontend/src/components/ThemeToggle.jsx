import { useTheme } from "../hooks/useTheme";

const OPTIONS = [
  { value: "light",  label: "Light", icon: "☀" },
  { value: "dark",   label: "Dark",  icon: "☽" },
  { value: "system", label: "Auto",  icon: "⊙" },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const next = () => {
    const idx = OPTIONS.findIndex((o) => o.value === theme);
    setTheme(OPTIONS[(idx + 1) % OPTIONS.length].value);
  };

  const current = OPTIONS.find((o) => o.value === theme) ?? OPTIONS[2];

  return (
    <button
      onClick={next}
      title={`Tema: ${current.label} — clique para alternar`}
      aria-label={`Tema atual: ${current.label}. Clique para alternar`}
      style={{
        background: "none",
        border: "1px solid var(--border)",
        borderRadius: 6,
        color: "var(--muted)",
        cursor: "pointer",
        fontSize: 14,
        padding: "4px 8px",
        lineHeight: 1,
        transition: "color 150ms, border-color 150ms",
        userSelect: "none",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = "var(--fg)";
        e.currentTarget.style.borderColor = "var(--muted)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = "var(--muted)";
        e.currentTarget.style.borderColor = "var(--border)";
      }}
    >
      {current.icon}
    </button>
  );
}
