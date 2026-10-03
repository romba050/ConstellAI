import React, { useEffect, useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, useEdgesState, useNodesState } from "reactflow";

function bubbleStyle(kind) {
  const base = {
    border: "1px solid rgba(233,236,255,0.18)",
    borderRadius: 999,
    padding: "10px 12px",
    fontWeight: 900,
    letterSpacing: "0.05em",
    background: "rgba(0,0,0,0.22)",
    boxShadow: "0 18px 55px rgba(0,0,0,0.25)",
    cursor: "pointer"
  };

  if (kind === "drug") return { ...base, borderColor: "rgba(125,249,255,0.28)" };
  if (kind === "group") return { ...base, borderColor: "rgba(255,204,102,0.22)", fontWeight: 800 };
  if (kind === "target") return { ...base, borderColor: "rgba(125,255,178,0.22)", fontWeight: 800 };
  return base;
}

function NodeBubble({ data }) {
  return (
    <div
      onClick={() => data?.onClick?.(data)}
      title={data?.hint || ""}
      style={bubbleStyle(data?.kind)}
    >
      <div style={{ fontSize: 12 }}>{data?.label}</div>
      {data?.sub ? <div style={{ fontSize: 10, opacity: 0.65, marginTop: 2 }}>{data.sub}</div> : null}
    </div>
  );
}

const nodeTypes = { bubble: NodeBubble };

export default function DrugGraph({ drug, onSelectTarget }) {
  const initial = useMemo(() => buildGraph(drug, onSelectTarget), [drug, onSelectTarget]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

  useEffect(() => {
    const g = buildGraph(drug, onSelectTarget);
    setNodes(g.nodes);
    setEdges(g.edges);
  }, [drug, onSelectTarget, setNodes, setEdges]);

  return (
    <div className="rfWrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}

function buildGraph(drug, onSelectTarget) {
  const nodes = [];
  const edges = [];

  const centerId = "drug";
  nodes.push({
    id: centerId,
    type: "bubble",
    position: { x: 0, y: 0 },
    data: { kind: "drug", label: drug?.name || "SELECT A DRUG", sub: drug?.category?.toUpperCase?.() || "", onClick: () => {} }
  });

  const groups = [
    { id: "receptors", label: "RECEPTORS", targets: drug?.activates?.receptors || [] },
    { id: "sirtuins", label: "SIRTUINS", targets: drug?.activates?.sirtuins || [] },
    { id: "genes", label: "GENES", targets: drug?.activates?.genes || [] }
  ];

  const angleStep = (Math.PI * 2) / Math.max(groups.length, 1);
  const radius = 210;

  groups.forEach((g, idx) => {
    const a = idx * angleStep - Math.PI / 2;
    const gx = Math.cos(a) * radius;
    const gy = Math.sin(a) * radius;

    nodes.push({
      id: g.id,
      type: "bubble",
      position: { x: gx, y: gy },
      data: { kind: "group", label: g.label, sub: `${g.targets.length} NODES`, onClick: () => {} }
    });

    edges.push({
      id: `e_${centerId}_${g.id}`,
      source: centerId,
      target: g.id,
      animated: true,
      style: { stroke: "rgba(233,236,255,0.22)" }
    });

    const tRadius = 170;
    const tStep = (Math.PI * 2) / Math.max(g.targets.length, 1);
    g.targets.slice(0, 10).forEach((t, j) => {
      const ta = j * tStep + a;
      const tx = gx + Math.cos(ta) * tRadius;
      const ty = gy + Math.sin(ta) * tRadius;

      const tid = `${g.id}_t_${j}`;
      nodes.push({
        id: tid,
        type: "bubble",
        position: { x: tx, y: ty },
        data: {
          kind: "target",
          label: t,
          sub: "CLICK",
          hint: "OPEN COMPOUNDS FOR THIS TARGET",
          onClick: () => onSelectTarget?.(t)
        }
      });

      edges.push({
        id: `e_${g.id}_${tid}`,
        source: g.id,
        target: tid,
        animated: false,
        style: { stroke: "rgba(233,236,255,0.14)" }
      });
    });
  });

  return { nodes, edges };
}
