import { SAMPLE, runPipeline, verifyChain } from "./pipeline.js";
const $ = (id) => document.getElementById(id);
let last = null;
function reset() { $("input").value = JSON.stringify(SAMPLE, null, 2); }
function graph(steps) {
  const w = 150, h = 60, gap = 20, perRow = 6;
  const rows = Math.ceil(steps.length / perRow);
  let svg = `<svg width="${perRow * (w + gap)}" height="${rows * (h + 40)}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="trace graph">`;
  steps.forEach((s, i) => {
    const x = (i % perRow) * (w + gap), y = Math.floor(i / perRow) * (h + 40);
    const fill = s.kind === "concept" ? "#5b4a12" : s.pass ? "#14532d" : "#7f1d1d";
    svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${fill}"/>`;
    svg += `<text x="${x + 6}" y="${y + 20}" fill="#fff" font-size="12">${s.id}</text>`;
    svg += `<text x="${x + 6}" y="${y + 40}" fill="#ddd" font-size="10" font-family="monospace">${s.link_hash.slice(0, 16)}…</text>`;
    if (i < steps.length - 1) {
      const nx = ((i + 1) % perRow) * (w + gap), ny = Math.floor((i + 1) / perRow) * (h + 40);
      svg += `<line x1="${x + w}" y1="${y + h / 2}" x2="${nx}" y2="${ny + h / 2}" stroke="#94a3b8" stroke-width="1.5"/>`;
    }
  });
  return svg + "</svg>";
}
function render({ steps, receipt }, chainOk) {
  $("graph").innerHTML = graph(steps);
  $("steps").innerHTML = steps.map((s) => `<div class="step" data-step="${s.id}"><b>${s.id}</b>
    <span class="badge ${s.kind}">${s.kind === "implemented" ? "Implemented" : "Concept (illustrative)"}</span>
    <span class="${s.pass ? "pass" : "fail"}">${s.pass ? "pass" : "fail"}</span>${s.advisory ? " <i>(advisory, does not gate promotion)</i>" : ""} — <i>${s.repo}</i>
    <div>output_hash <code>${s.output_hash}</code></div><div>link_hash <code>${s.link_hash}</code></div>
    <details><summary>output</summary><pre>${JSON.stringify(s.output, null, 2).replace(/</g, "&lt;")}</pre></details></div>`).join("");
  $("receipt").textContent = JSON.stringify(receipt, null, 2);
  $("chain").innerHTML = `Hash chain verification: <b id="chain-status" class="${chainOk ? "pass" : "fail"}">${chainOk ? "VALID" : "BROKEN"}</b>`;
}
async function run() {
  let input; try { input = JSON.parse($("input").value); } catch (e) { alert("Invalid JSON: " + e.message); return; }
  last = await runPipeline(input);
  render(last, await verifyChain(last.steps));
}
$("run").onclick = run; $("reset").onclick = () => { reset(); run(); };
$("tamper").onclick = async () => { if (!last) return; last.steps[2].output = { tampered: true }; render(last, await verifyChain(last.steps)); };
reset(); run();
