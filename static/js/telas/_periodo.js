/* Utilitários de período e gráficos usados por Relatórios e Financeiro. */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc } = P;

  const FORMAS = { dinheiro: "Dinheiro", pix: "Pix", cartao_debito: "Cartão de débito", cartao_credito: "Cartão de crédito" };
  const forma = v => esc(FORMAS[v] || v || "—");
  const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  function periodoPadrao() {
    const hoje = new Date();
    return { inicio: iso(new Date(hoje.getFullYear(), hoje.getMonth(), 1)), fim: iso(hoje) };
  }

  function formPeriodo(extra = "") {
    const p = periodoPadrao();
    return `<form id="period-form" class="toolbar">
      <label class="field">De<input type="date" name="inicio" value="${p.inicio}" required></label>
      <label class="field">Até<input type="date" name="fim" value="${p.fim}" required></label>
      <button class="btn btn-primary">Atualizar</button>${extra}</form>`;
  }

  /* Barras horizontais simples feitas com HTML/CSS (sem biblioteca de gráficos). */
  function barras(itens, rotulo, valor, formato = v => v) {
    const maximo = Math.max(1, ...itens.map(i => Number(i[valor])));
    return `<div class="bars">${itens.map(i => {
      const v = Number(i[valor]);
      return `<div class="bar-row"><span>${esc(i[rotulo])}</span><div class="bar"><i style="width:${(v / maximo * 100).toFixed(1)}%"></i></div><b>${esc(formato(v))}</b></div>`;
    }).join("")}</div>`;
  }

  P.util = { FORMAS, forma, iso, periodoPadrao, formPeriodo, barras };
})();
