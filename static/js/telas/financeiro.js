/* Tela: financeiro */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { $, esc, money, dt, date, api, panel, table, stat, badge, catchForm, fmtDuracao } = P;
  const { forma, formPeriodo, barras } = P.util;

  /* ---------- Financeiro ---------- */
  P.telas.financeiro = async function financeiro() {
    const root = $("#app-content");
    root.innerHTML = panel("Período", "Os recebimentos consideram a data em que o pagamento foi confirmado", formPeriodo()) + `<div id="finance-result"></div>`;

    async function carregar() {
      const f = $("#period-form"), q = `inicio=${f.elements.inicio.value}&fim=${f.elements.fim.value}`;
      const [r, atrasos, caixas] = await Promise.all([api(`/api/financeiro/resumo?${q}`), api("/api/financeiro/inadimplencia"), api(`/api/financeiro/caixas?${q}`)]);
      $("#finance-result").innerHTML = `<div class="stats-grid">${stat("Total recebido", money(r.total_recebido), "＄", `${r.recebimentos} recebimento(s)`)}${stat("Ticket médio (horista)", money(r.ticket_medio_horista), "◉", "Valor médio por saída paga")}${stat("Permanência média", fmtDuracao(r.permanencia_media_minutos), "◷", `${r.saidas} saída(s) no período`)}${stat("Mensalidades em atraso", r.em_atraso.quantidade, "⚠", money(r.em_atraso.total))}</div>`
        + `<div class="notice notice-info">Mensalidades abertas (a vencer ou vencidas): <strong>${esc(r.a_receber.quantidade)}</strong>, somando <strong>${money(r.a_receber.total)}</strong>.</div>`
        + `<div class="columns-2"><div>${panel("Por forma de pagamento", "", table([{ key: "forma_pagamento", label: "Forma", render: forma }, { key: "quantidade", label: "Qtd." }, { key: "total", label: "Total", render: money }], r.por_forma, "Nenhum recebimento no período."))}</div>`
        + `<div>${panel("Por origem", "", table([{ key: "origem", label: "Origem", render: v => esc(v === "mensalidade" ? "Mensalidades" : "Horistas") }, { key: "quantidade", label: "Qtd." }, { key: "total", label: "Total", render: money }], r.por_origem, "Nenhum recebimento no período."))}</div></div>`
        + panel("Receita por dia", "Valor recebido em cada dia do período", r.por_dia.length ? barras(r.por_dia.map(d => ({ ...d, rotulo: date(d.dia) })), "rotulo", "total", money) : `<div class="empty-row">Nenhum recebimento no período.</div>`)
        + panel("Inadimplência", "Mensalidades vencidas e não pagas (já descontada a carência das configurações)", table([
          { key: "cliente_nome", label: "Cliente" }, { key: "placa", label: "Placa" }, { key: "telefone", label: "Telefone" },
          { key: "competencia", label: "Competência", render: date }, { key: "vencimento", label: "Vencimento", render: date },
          { key: "dias_atraso", label: "Dias em atraso", render: v => badge(`${v} dia(s) · atraso`) }, { key: "valor", label: "Valor", render: money }], atrasos, "Nenhuma mensalidade em atraso."))
        + panel("Fechamentos de caixa", "Diferença = dinheiro contado menos dinheiro esperado", table([
          { key: "aberto_em", label: "Abertura", render: dt }, { key: "fechado_em", label: "Fechamento", render: v => v ? dt(v) : badge("Aberto") }, { key: "operador", label: "Operador" },
          { key: "dinheiro_esperado", label: "Esperado", render: v => v == null ? "—" : money(v) }, { key: "dinheiro_contado", label: "Contado", render: v => v == null ? "—" : money(v) },
          { key: "diferenca", label: "Diferença", render: v => v == null ? "—" : `<span class="${Number(v) === 0 ? "diff-ok" : "diff-alerta"}">${money(v)}</span>` }, { key: "observacao", label: "Observação" }], caixas, "Nenhum caixa no período."));
    }

    catchForm($("#period-form"), carregar);
    await carregar();
  };
})();
