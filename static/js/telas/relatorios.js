/* Tela: relatorios */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { $, esc, money, dt, api, panel, table, stat, catchForm } = P;
  const { forma, formPeriodo, barras } = P.util;

  /* ---------- Relatórios ---------- */
  P.telas.relatorios = async function relatorios() {
    const root = $("#app-content");
    root.innerHTML = panel("Período do relatório", "Escolha as datas e exporte em CSV para abrir no Excel", `${formPeriodo(`<span id="export-links" class="export-links"></span>`)}`) + `<div id="report-result"></div>`;

    async function carregar() {
      const f = $("#period-form"), q = `inicio=${f.elements.inicio.value}&fim=${f.elements.fim.value}`;
      $("#export-links").innerHTML = `<a class="btn btn-secondary" href="/api/relatorios/movimentacoes.csv?${q}">Exportar movimentações (CSV)</a> <a class="btn btn-secondary" href="/api/relatorios/recebimentos.csv?${q}">Exportar recebimentos (CSV)</a>`;
      const [ocup, movs, receb] = await Promise.all([api(`/api/relatorios/ocupacao?${q}`), api(`/api/relatorios/movimentacoes?${q}`), api(`/api/relatorios/recebimentos?${q}`)]);
      const totalValor = receb.reduce((s, r) => s + Number(r.valor || 0), 0);
      $("#report-result").innerHTML = `<div class="stats-grid">${stat("Entradas no período", ocup.total_entradas, "↕", "Veículos que entraram")}${stat("Horário de pico", ocup.hora_de_pico || "—", "◔", "Hora com mais entradas")}${stat("Recebimentos", receb.length, "◉", "Pagamentos confirmados")}${stat("Total recebido", money(totalValor), "＄", "Soma do período")}</div>`
        + `<div class="columns-2"><div>${panel("Entradas por hora", "Ajuda a escalar a equipe nos horários de pico", barras(ocup.por_hora, "rotulo", "entradas"))}</div><div>${panel("Entradas por dia da semana", "Distribuição no período", barras(ocup.por_dia_semana, "rotulo", "entradas"))}</div></div>`
        + panel("Movimentações", `${movs.length} registro(s). A tela mostra os 200 mais recentes; o CSV traz todos.`, table([
          { key: "placa", label: "Placa" }, { key: "tipo_veiculo", label: "Tipo" }, { key: "plano", label: "Plano" }, { key: "vaga", label: "Vaga" },
          { key: "entrada_em", label: "Entrada", render: dt }, { key: "saida_em", label: "Saída", render: dt }, { key: "tempo", label: "Permanência" },
          { key: "valor", label: "Valor", render: money }, { key: "operador", label: "Operador" }], movs.slice(0, 200)))
        + panel("Recebimentos", `${receb.length} registro(s). A tela mostra os 200 mais recentes.`, table([
          { key: "pago_em", label: "Pago em", render: dt }, { key: "origem", label: "Origem" }, { key: "cliente", label: "Cliente" }, { key: "placa", label: "Placa" },
          { key: "forma_pagamento", label: "Forma", render: forma }, { key: "valor", label: "Valor", render: money }], receb.slice(0, 200)));
    }

    catchForm($("#period-form"), carregar);
    await carregar();
  };
})();
