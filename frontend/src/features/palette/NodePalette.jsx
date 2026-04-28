import { NODE_TYPES } from "../../utils/formatters";

export function NodePalette() {
  const handleDragStart = (e, key) => {
    e.dataTransfer.setData("nodeType", key);
    e.dataTransfer.effectAllowed = "copy";
  };

  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
      {Object.entries(NODE_TYPES).map(([key, nt]) => (
        <div
          key={key}
          draggable
          onDragStart={(e) => handleDragStart(e, key)}
          style={{
            display: "flex", alignItems: "center", gap: 6, padding: "6px 12px",
            background: "var(--surface)", borderRadius: 6, border: `1px solid ${nt.color}30`,
            cursor: "grab", fontSize: 11, userSelect: "none", transition: "border-color 0.15s",
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = nt.color}
          onMouseLeave={e => e.currentTarget.style.borderColor = `${nt.color}30`}
        >
          <span>{nt.icon}</span>
          <span style={{ color: nt.color, fontWeight: 500 }}>{nt.label}</span>
        </div>
      ))}
      <div style={{ fontSize: 10, color: "var(--muted)", alignSelf: "center", marginLeft: 4 }}>
        ← arraste ao canvas
      </div>
    </div>
  );
}
