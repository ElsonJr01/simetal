// Gráfico antes/depois (Plotly). Redesenha após cada troca do HTMX.
function drawCharts(root) {
  const el = (root || document).querySelector("#chart[data-chart]");
  if (!el || !window.Plotly) return;
  const data = JSON.parse(el.dataset.chart || "null");
  if (!data) return;
  const css = getComputedStyle(document.documentElement);
  const traces = [
    { x: data.nomes, y: data.entrada, name: "Entrada", type: "bar", marker: { color: css.getPropertyValue("--brand-line").trim() } },
    { x: data.nomes, y: data.ajustado, name: "Ajustado", type: "bar", marker: { color: css.getPropertyValue("--brand-primary").trim() } },
  ];
  Plotly.newPlot(el, traces, {
    barmode: "group", margin: { t: 20, r: 10, b: 40, l: 60 },
    xaxis: { title: "Fluxo" }, legend: { orientation: "h" },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: css.getPropertyValue("--font-body").trim() },
  }, { responsive: true, displaylogo: false });
}
window.addEventListener("load", () => drawCharts());
document.body.addEventListener("htmx:afterSwap", (e) => drawCharts(e.target));
