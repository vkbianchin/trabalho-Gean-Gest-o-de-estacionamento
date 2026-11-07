/* Tela: pagamentos */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, money, date, toast, api, fd, field, select, badge, table, stat, panel, modal, catchForm, wireSearch, pedirMotivo, ehAdmin } = P;
  const $ = P.$;
  const $$ = P.$$;

  async function payments(){
    const rows=await api("/api/pagamentos"),pending=rows.filter(r=>r.situacao==="aberto");
    $("#app-content").innerHTML=`<div class="stats-grid">${stat("Cobranças listadas",rows.length,"◉","Registros recentes")}${stat("Em aberto",pending.length,"◷","Aguardando recebimento")}${stat("Total em aberto",money(pending.reduce((s,r)=>s+Number(r.valor||0),0)),"＄","Somatório pendente")}${stat("Pagas",rows.filter(r=>r.situacao==="pago").length,"✓","Recebimentos confirmados")}</div>${panel("Pagamentos e mensalidades","Recebimentos exigem caixa aberto.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar cliente, placa ou situação..."></label><button class="btn btn-secondary" id="generate-bills">Gerar mensalidades do mês</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"id",label:"Nº"},{key:"cliente_nome",label:"Cliente",render:v=>v||"Horista"},{key:"placa",label:"Placa"},{key:"competencia",label:"Competência",render:date},{key:"vencimento",label:"Vencimento",render:date},{key:"valor",label:"Valor",render:money},{key:"situacao",label:"Situação",render:badge},{key:"forma_pagamento",label:"Forma"},{key:"acao",label:"Ação",render:(v,r)=>{const id=esc(r.id??r.pagamento_id),admin=ehAdmin();if(r.situacao==="aberto")return((r.contrato_id?`<button class="btn btn-primary btn-sm" data-receive="${id}">Receber</button>`:"")+(admin?` <button class="btn btn-secondary btn-sm" data-cancel="${id}" data-acao="Cancelar">Cancelar</button>`:""))||"—";if(r.situacao==="pago")return `<a class="btn btn-secondary btn-sm" target="_blank" rel="noopener" href="/recibo/pagamento/${id}">Recibo</a>`+(admin?` <button class="btn btn-danger btn-sm" data-cancel="${id}" data-acao="Estornar">Estornar</button>`:"");return "—";}}],rows)}</div>`)}`;
    wireSearch($("#search-table"),$("#table-results"));
    $("#generate-bills").onclick=async()=>{try{const r=await api("/api/pagamentos/gerar-mensalidades",{method:"POST",body:JSON.stringify({})});toast(`${r.criadas??0} mensalidade(s) gerada(s).`);await payments();}catch(e){toast(e.message,"error");}};
    // Estorno (pagamento recebido) e cancelamento (cobrança em aberto): exigem motivo e ficam na auditoria.
    $$("[data-cancel]").forEach(b=>b.addEventListener("click",async()=>{
      const acao=b.dataset.acao;
      const motivo=await pedirMotivo(`${acao} pagamento`,acao==="Estornar"?"O valor deixa de contar no caixa. Mensalidade volta para em aberto; pagamento de horista fica cancelado.":"A cobrança deixa de existir. A ação fica registrada na auditoria.",acao);
      if(!motivo)return;
      try{const r=await api(`/api/pagamentos/${b.dataset.cancel}/cancelar`,{method:"POST",body:JSON.stringify({motivo})});toast(r.mensagem);await payments();}catch(e){toast(e.message,"error");}
    }));
    $$("[data-receive]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.receive;modal("Receber mensalidade",`<form id="receive-form" class="form-stack"><label>Forma de pagamento<select name="forma_pagamento" required><option value="dinheiro">Dinheiro</option><option value="pix">Pix</option><option value="cartao_debito">Cartão de débito</option><option value="cartao_credito">Cartão de crédito</option></select></label><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Confirmar recebimento</button></div></form>`);catchForm($("#receive-form"),async e=>{await api(`/api/pagamentos/${id}/receber`,{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Pagamento recebido.");await payments();});}));
  }

  P.telas.pagamentos = payments;
})();
