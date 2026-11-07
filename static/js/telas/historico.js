/* Tela: historico */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { $, esc, money, dt, date, api, panel, table, stat, badge, catchForm } = P;

  /* ---------- Histórico por veículo ---------- */
  P.telas.historico = async function historico() {
    const root = $("#app-content");
    root.innerHTML = panel("Consultar placa", "Digite a placa para ver todas as passagens pelo estacionamento",
      `<form id="history-form" class="toolbar"><label class="field search"><input name="placa" placeholder="ABC1D23" maxlength="8" autocapitalize="characters" autocomplete="off" required></label><button class="btn btn-primary">Consultar</button></form>`) + `<div id="history-result"></div>`;
    const campo = $("#history-form").elements.placa;

    async function buscar(placa) {
      const saida = $("#history-result");
      saida.innerHTML = `<div class="loading-panel"><span class="spinner"></span>Consultando...</div>`;
      try {
        const r = await api(`/api/historico/${encodeURIComponent(placa)}`);
        const t = r.totais, c = r.cadastro;
        const cadastro = c
          ? `<div class="notice notice-info">Veículo cadastrado: <strong>${esc(c.tipo_nome)}</strong>${c.modelo ? ` · ${esc(c.modelo)}` : ""}${c.cor ? ` · ${esc(c.cor)}` : ""} · cliente <strong>${esc(c.cliente_nome)}</strong>.</div>`
          : `<div class="notice notice-info">Esta placa não está vinculada a um cliente cadastrado.</div>`;
        saida.innerHTML = cadastro + `<div class="stats-grid">${stat("Visitas", t.visitas, "↕", t.no_local ? "Veículo está no local agora" : "Passagens registradas")}${stat("Total pago", money(t.total_gasto), "＄", "Soma dos valores cobrados")}${stat("Tempo médio", t.tempo_medio || "—", "◷", "Por visita concluída")}${stat("Última visita", t.ultima_visita ? date(t.ultima_visita) : "—", "▦", t.primeira_visita ? `Primeira em ${date(t.primeira_visita)}` : "Sem registros")}</div>`
          + panel(`Passagens de ${esc(r.placa)}`, "Da mais recente para a mais antiga", table([
            { key: "entrada_em", label: "Entrada", render: dt },
            { key: "saida_em", label: "Saída", render: (v, l) => l.no_local ? badge("No local") : dt(v) },
            { key: "tempo", label: "Permanência", render: v => esc(v || "—") },
            { key: "vaga", label: "Vaga" }, { key: "tipo_veiculo", label: "Tipo" }, { key: "plano", label: "Plano" },
            { key: "valor", label: "Valor", render: money }, { key: "operador", label: "Operador" },
            { key: "cancelada", label: "Obs.", render: (v, l) => [l.cancelada ? badge("Cancelada") : "", l.retroativa ? badge("Retroativa") : ""].join(" ") || "—" },
          ], r.passagens, "Nenhuma passagem registrada para esta placa."));
      } catch (e) {
        saida.innerHTML = `<div class="notice notice-error">${esc(e.message)}</div>`;
      }
    }

    catchForm($("#history-form"), async () => {
      const placa = campo.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      history.replaceState(null, "", `/historico?placa=${encodeURIComponent(placa)}`);
      await buscar(placa);
    });
    const inicial = new URLSearchParams(location.search).get("placa");
    if (inicial) { campo.value = inicial.toUpperCase(); await buscar(campo.value.replace(/[^A-Z0-9]/g, "")); }
  };
})();
