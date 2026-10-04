/* Helpers shared by the dashboard and the atlas page. */
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const api = async (path) => {
  const r = await fetch(path);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
};
const plural = (n, w) => `${n} ${n === 1 ? w : w.endsWith("y") ? w.slice(0, -1) + "ies" : w + "s"}`;
const link = (url, text) => (url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)}</a>` : esc(text));
const refLink = (ref) => {
  const [db, id] = ref.split(":");
  const url = db === "PMID" ? `https://pubmed.ncbi.nlm.nih.gov/${id}/` : db === "OMIM" ? `https://omim.org/entry/${id}`
    : db === "ORPHA" ? `https://www.orpha.net/en/disease/detail/${id}` : "";
  return link(url, ref);
};

/* The copy/download sheet used for proposals and enquiry e-mails. */
function openSheet(text, title = "Ready to send") {
  $("#sheet-title").textContent = title; $("#brief").textContent = text; $("#modal").hidden = false;
}
$("#close").onclick = () => ($("#modal").hidden = true);
$("#modal").addEventListener("click", (ev) => { if (ev.target.id === "modal") $("#modal").hidden = true; });
$("#copy").onclick = async () => {
  await navigator.clipboard.writeText($("#brief").textContent);
  $("#copy").textContent = "Copied"; setTimeout(() => ($("#copy").textContent = "Copy"), 1500);
};
$("#download").onclick = () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([$("#brief").textContent], { type: "text/markdown" }));
  a.download = "constellai.md"; a.click(); URL.revokeObjectURL(a.href);
};
