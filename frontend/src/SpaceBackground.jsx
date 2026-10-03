import React from "react";

export default function SpaceBackground() {
  return (
    <div
      className="space-canvas"
      aria-hidden="true"
      style={{ background: "linear-gradient(180deg, #0b1020 0%, #111827 54%, #0f172a 100%)" }}
    />
  );
}
