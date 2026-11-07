/* Tela: contratos */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, money, date, toast, api, fd, moneyField, field, select, badge, table, panel, modal, catchForm, wireSearch } = P;
  const $ = P.$;
  const $$ = P.$$;

  async function contracts(){
    const [rows,clientes,veiculos]=await Promise.all([api("/api/contratos"),api("/api/clientes"),api("/api/veiculos")]);
    $("#app-content").innerHTML=panel("Contratos mensalistas","Um contrato por veículo; valor mensal registrado no momento da contratação.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar cliente ou placa..."></label><button class="btn btn-primary" id="new-contract">＋ Novo contrato</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"id",label:"Nº"},{key:"cliente_nome",label:"Cliente"},{key:"placa",label:"Placa"},{key:"valor_mensal",label:"Mensalidade",render:money},{key:"dia_vencimento",label:"Vencimento",render:v=>`Dia ${esc(v)}`},{key:"data_inicio",label:"Início",render:date},{key:"data_fim",label:"Fim",render:date},{key:"situacao",label:"Status",render:(v,r)=>badge(r.data_fim?"Encerrado":"Vigente")},{key:"acao",label:"Ação",render:(v,r)=>!r.data_fim?`<button class="btn btn-secondary btn-sm" data-end="${esc(r.id??r.contrato_id)}">Encerrar</button>`:"—"}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $("#new-contract").onclick=()=>{modal("Novo contrato mensalista",`<form id="contract-form" class="form-grid">${select("Cliente","cliente_id",clientes.map(c=>({value:c.id??c.cliente_id,label:c.nome})))}${select("Veículo","veiculo_id",veiculos.map(v=>({value:v.id??v.veiculo_id,label:`${v.placa} · ${v.cliente_nome||""}`})))}${moneyField("Valor mensal (R$)","valor_mensal",true)}${field("Dia de vencimento","dia_vencimento","number",true,"1 a 28",'min="1" max="28"')}${field("Data de início","data_inicio","date")}<div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Criar contrato</button></div></form>`);
    catchForm($("#contract-form"),async e=>{const d=fd(e.currentTarget);["cliente_id","veiculo_id","dia_vencimento"].forEach(k=>d[k]=Number(d[k]));await api("/api/contratos",{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Contrato criado.");await contracts();});};
    $$("[data-end]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.end;modal("Encerrar contrato",`<form id="end-contract-form" class="form-stack"><label>Data de encerramento<input name="data_fim" type="date" required value="${new Date().toLocaleDateString("en-CA")}"></label><label>Motivo<select name="motivo"><option value="cancelado_cliente">Cancelado pelo cliente</option><option value="inadimplencia">Inadimplência</option><option value="troca_veiculo">Troca de veículo</option><option value="outro">Outro</option></select></label><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-danger">Encerrar contrato</button></div></form>`);catchForm($("#end-contract-form"),async e=>{await api(`/api/contratos/${id}/encerrar`,{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Contrato encerrado.");await contracts();});}));
  }

  P.telas.contratos = contracts;
})();
