/* Tela: painel */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { dt, toast, api, table, stat, panel, go } = P;
  const $ = P.$;
  const $$ = P.$$;

  async function dashboard(){
    const root=$("#app-content");const [vagas,movs,caixa]=await Promise.all([api("/api/vagas"),api("/api/movimentacoes"),api("/api/caixa")]);
    const open=movs.filter(m=>!m.saida_em&&!Number(m.cancelada));const occupied=vagas.filter(v=>v.ocupada===true||Number(v.ocupada)===1).length;
    root.innerHTML=`<div class="welcome-card"><div><span class="eyebrow">VISÃO GERAL</span><h2>Operação do estacionamento</h2><p>Acompanhe a ocupação e registre movimentos pela placa.</p></div><div class="welcome-icon">▤</div></div><div class="stats-grid">${stat("Vagas cadastradas",vagas.length,"▦","Total configurado")}${stat("Vagas livres",Math.max(0,vagas.length-occupied),"✓","Disponibilidade atual")}${stat("Vagas ocupadas",occupied,"▰","Ocupação atual")}${stat("Veículos no local",open.length,"↕","Movimentações abertas")}</div><div class="columns-2"><div>${panel("Movimentações abertas","Veículos que ainda estão no estacionamento",table([{key:"placa",label:"Placa"},{key:"vaga_numero",label:"Vaga"},{key:"entrada_em",label:"Entrada",render:dt}],open.slice(0,8),"Nenhum veículo estacionado."),`<a class="btn btn-secondary btn-sm" href="/movimentacoes">Ver todas →</a>`)}</div><div>${panel("Acesso rápido","Atalhos para tarefas do turno",`<div class="quick-actions"><button class="quick-action" data-go="/movimentacoes">↕<strong>Entrada / saída</strong><small>Registrar movimento de veículo</small></button><button class="quick-action" data-go="/caixa">＄<strong>Controle de caixa</strong><small>Abrir ou fechar o caixa</small></button><button class="quick-action" data-go="/clientes">♙<strong>Cadastrar cliente</strong><small>Dados dos mensalistas</small></button><button class="quick-action" data-go="/pagamentos">◉<strong>Mensalidades</strong><small>Consultar cobranças</small></button></div>`)}</div></div>`;
    $$("[data-go]").forEach(b=>b.addEventListener("click",()=>go(b.dataset.go)));
    if(!caixa.aberto)toast("O caixa está fechado. Abra-o antes de receber pagamentos.","error");
  }

  P.telas.painel = dashboard;
})();
