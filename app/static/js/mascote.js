// Mascote de dicas: busca /api/v1/dicas (API aberta) e mostra uma dica por vez.
// O progresso (dicas vistas) fica só no navegador (localStorage); nada é enviado ao servidor.
(function () {
  const root = document.getElementById("mascote");
  if (!root) return;
  const KEY_SEEN = "simetal.dicas.vistas", KEY_MUTE = "simetal.dicas.silencio";
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sem armazenamento */ } },
  };
  const ctx = document.body.dataset.tipContext || "geral";
  const contexts = [...new Set([...ctx.split(","), "geral"])].join(",");
  let tips = [], current = null;

  const seen = () => new Set(store.get(KEY_SEEN, []));
  function pick(skipId) {
    const s = seen();
    const pool = tips.filter((t) => t.id !== skipId);
    const unseen = pool.filter((t) => !s.has(t.id));
    const list = unseen.length ? unseen : pool;
    return list[unseen.length ? 0 : Math.floor(Math.random() * list.length)] || null;
  }
  function show(tip) {
    if (!tip) return;
    current = tip;
    $("mascote-titulo").textContent = tip.titulo;
    $("mascote-texto").textContent = tip.texto;
    $("mascote-balao").hidden = false;
    $("mascote-botao").setAttribute("aria-expanded", "true");
  }
  function hide() {
    $("mascote-balao").hidden = true;
    $("mascote-botao").setAttribute("aria-expanded", "false");
  }
  $("mascote-botao").addEventListener("click", () => ($("mascote-balao").hidden ? show(current || pick()) : hide()));
  $("mascote-proxima").addEventListener("click", () => show(pick(current && current.id)));
  $("mascote-entendi").addEventListener("click", () => {
    if (current) { const s = seen(); s.add(current.id); store.set(KEY_SEEN, [...s]); }
    hide(); current = null;
  });
  $("mascote-silenciar").addEventListener("click", () => { store.set(KEY_MUTE, true); hide(); });

  fetch("/api/v1/dicas?contexto=" + encodeURIComponent(contexts))
    .then((r) => (r.ok ? r.json() : []))
    .then((data) => {
      // dicas da página atual primeiro, gerais depois
      const order = ctx.split(",");
      tips = data.sort((a, b) => (order.indexOf(a.contexto) + 1 || 99) - (order.indexOf(b.contexto) + 1 || 99));
      if (!tips.length) return;
      root.hidden = false;
      const first = pick();
      if (first && !store.get(KEY_MUTE, false) && !seen().has(first.id)) setTimeout(() => show(first), 1500);
    })
    .catch(() => { /* sem dicas: o mascote simplesmente não aparece */ });
})();
