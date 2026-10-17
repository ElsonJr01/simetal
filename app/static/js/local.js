// Selects de estado e município alimentados pela API de Localidades do IBGE (via backend, com cache).
(function () {
  const form = document.getElementById("local-form");
  if (!form) return;
  const ufSel = document.getElementById("local-uf"), munSel = document.getElementById("local-municipio");
  const option = (v, t) => Object.assign(document.createElement("option"), { value: v, textContent: t });
  const fail = (sel, msg) => { sel.replaceChildren(option("", msg)); };

  async function loadMunicipios(uf, selected) {
    if (!uf) return fail(munSel, "Escolha o estado");
    fail(munSel, "Carregando…");
    try {
      const r = await fetch(`/api/v1/ibge/estados/${encodeURIComponent(uf)}/municipios`);
      if (!r.ok) throw new Error();
      const cities = await r.json();
      munSel.replaceChildren(option("", "Escolha o município"), ...cities.map((c) => option(c.id, c.nome)));
      if (selected) munSel.value = selected;
    } catch { fail(munSel, "IBGE indisponível no momento"); }
  }

  (async function init() {
    try {
      const r = await fetch("/api/v1/ibge/estados");
      if (!r.ok) throw new Error();
      const states = await r.json();
      ufSel.replaceChildren(option("", "Escolha o estado"), ...states.map((s) => option(s.sigla, `${s.nome} (${s.sigla})`)));
      if (form.dataset.uf) { ufSel.value = form.dataset.uf; loadMunicipios(form.dataset.uf, form.dataset.municipio); }
    } catch { fail(ufSel, "IBGE indisponível no momento"); }
  })();
  ufSel.addEventListener("change", () => loadMunicipios(ufSel.value));
})();
