/* Tela: caixa */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { money, toast, api, fd, moneyField, field, stat, panel, catchForm, updateCashIndicator } = P;
  const $ = P.$;

  async function cash(){
    const root=$("#app-content"),c=await api("/api/caixa");
    if(!c.aberto){root.innerHTML=panel("Abrir caixa","Informe o troco inicial para começar o turno.",`<form id="open-cash" class="form-stack content-narrow">${moneyField("Troco inicial (R$)","valor_inicial",true,"0.00")}<div class="notice notice-info">O caixa precisa estar aberto para receber pagamentos. A operação de entrada de veículos continua disponível.</div><button class="btn btn-primary">Abrir caixa</button></form>`);catchForm($("#open-cash"),async e=>{await api("/api/caixa/abrir",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});toast("Caixa aberto.");await cash();await updateCashIndicator();});return;}
    root.innerHTML=`<div class="stats-grid">${stat("Situação","Aberto","✓","Caixa deste turno")}${stat("Troco inicial",money(c.valor_inicial),"＄","Valor informado na abertura")}${stat("Dinheiro esperado",money(c.dinheiro_esperado),"◉","Troco + pagamentos em dinheiro")}${stat("Identificação",c.id??c.caixa_id??"Atual","▤","Número do caixa")}</div>${panel("Fechar caixa","Conte o dinheiro físico. O sistema calcula a diferença.",`<form id="close-cash" class="form-grid"><label>Dinheiro contado (R$)<input name="dinheiro_contado" type="number" min="0" step=".01" required></label>${field("Observação (opcional)","observacao","text",false,"Observações do fechamento",'maxlength="250"')}<div class="form-actions span-2"><button class="btn btn-danger">Fechar caixa</button></div></form>`)}`;
    catchForm($("#close-cash"),async e=>{if(!confirm("Confirma o fechamento do caixa?"))return;const r=await api("/api/caixa/fechar",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});toast(r.diferenca!==undefined?`Caixa fechado. Diferença: ${money(r.diferenca)}`:"Caixa fechado.");await cash();await updateCashIndicator();});
  }

  P.telas.caixa = cash;
})();
