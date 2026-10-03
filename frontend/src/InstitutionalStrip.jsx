import React from "react";

export default function InstitutionalStrip() {
  return (
    <div
      style={{
        marginTop: 10,
        padding: "8px 10px",
        borderRadius: 10,
        border: "1px solid rgba(190,201,226,0.16)",
        background: "rgba(12,17,30,0.92)",
        fontSize: 12,
        letterSpacing: 0.3,
        display: "flex",
        gap: 10,
        flexWrap: "wrap",
        alignItems: "center",
        color: "rgba(240,245,255,0.84)",
      }}
    >
      <span>research workspace</span>
      <span>•</span>
      <span>human review required</span>
      <span>•</span>
      <span>traceable exports</span>
      <span>•</span>
      <span>backend connected</span>
    </div>
  );
}
