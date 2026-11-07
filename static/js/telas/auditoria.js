/* Tela: auditoria */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, dt, api, field, badge, table, panel, modal, wireSearch } = P;
  const $ = P.$;
  const $$ = P.$$;

  async function audit(){
    const rows=await api("/api/auditoria");
    $("#app-content").innerHTML=panel("Registro de auditoria","Alterações administrativas registradas pelo sistema.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar tabela, ação ou usuário..."></label></div><div style="height:15px"></div><div id="table-results">${table([{key:"data_hora",label:"Data e hora",render:dt},{key:"usuario_nome",label:"Usuário"},{key:"tabela",label:"Tabela"},{key:"registro_id",label:"Registro"},{key:"acao",label:"Ação",render:badge},{key:"dados_antes",label:"Antes",render:v=>v?`<button class="btn btn-secondary btn-sm" data-json="${esc(v)}">Ver</button>`:"—"},{key:"dados_depois",label:"Depois",render:v=>v?`<button class="btn btn-secondary btn-sm" data-json="${esc(v)}">Ver</button>`:"—"}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $$("[data-json]").forEach(b=>b.addEventListener("click",()=>{let val=b.dataset.json;try{val=JSON.stringify(JSON.parse(val),null,2)}catch{}modal("Detalhes do registro",`<pre class="json-view">${esc(val)}</pre>`);}));
  }

  P.telas.auditoria = audit;
})();
