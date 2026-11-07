/* Tela: veiculos */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, toast, api, fd, field, select, badge, table, panel, fmtDoc, modal, catchForm, wireSearch, confirmar, ehAdmin } = P;
  const $ = P.$;
  const $$ = P.$$;

  const acoesVeiculo=r=>{const ativo=Number(r.ativo)===1;return `<button class="btn btn-secondary btn-sm" data-edit="${esc(r.id)}">Editar</button>`+(ehAdmin()?` <button class="btn ${ativo?"btn-danger":"btn-secondary"} btn-sm" data-toggle="${esc(r.id)}" data-ativo="${ativo?0:1}">${ativo?"Desativar":"Ativar"}</button>`:"");};
  async function vehicles(){
    const [rows,clientes,tipos,modelos,cores,marcas]=await Promise.all([api("/api/veiculos"),api("/api/clientes"),api("/api/catalogos/tipos_veiculo"),api("/api/catalogos/modelos"),api("/api/catalogos/cores"),api("/api/catalogos/marcas")]);
    $("#app-content").innerHTML=panel("Veículos cadastrados","Cada veículo mensalista deve estar vinculado a um cliente",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar placa, cliente ou modelo..."></label><button class="btn btn-primary" id="new-vehicle">＋ Novo veículo</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"placa",label:"Placa"},{key:"cliente_nome",label:"Cliente"},{key:"tipo_veiculo",label:"Tipo"},{key:"modelo",label:"Modelo"},{key:"cor",label:"Cor"},{key:"ativo",label:"Status",render:badge},{key:"placa",label:"",render:v=>`<a class="btn btn-secondary btn-sm" href="/historico?placa=${encodeURIComponent(v)}">Histórico</a>`},{key:"id",label:"",render:(id,r)=>acoesVeiculo(r)}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    // Editar (modelo e cor) e ativar/desativar. A placa, o dono e o tipo não mudam.
    $("#table-results").addEventListener("click",async e=>{
      const editar=e.target.closest("[data-edit]"),alternar=e.target.closest("[data-toggle]");
      try{
        if(editar){
          const veic=await api(`/api/veiculos/${editar.dataset.edit}`);
          const doTipo=modelos.filter(m=>m.tipo_veiculo_id==null||Number(m.tipo_veiculo_id)===Number(veic.tipo_veiculo_id));
          modal(`Editar veículo ${veic.placa}`,`<form id="vehicle-edit-form" class="form-grid">${select("Modelo (opcional)","modelo_id",doTipo.map(m=>({value:m.id,label:m.nome})),false)}${select("Cor (opcional)","cor_id",cores.map(c=>({value:c.id,label:c.nome})),false)}<small class="span-2">A placa, o dono e o tipo do veículo não mudam. Para corrigi-los, cadastre um novo veículo.</small><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar alterações</button></div></form>`);
          const form=$("#vehicle-edit-form");form.elements.modelo_id.value=veic.modelo_id??"";form.elements.cor_id.value=veic.cor_id??"";
          catchForm(form,async ev=>{const d=fd(ev.currentTarget);const corpo={modelo_id:d.modelo_id?Number(d.modelo_id):null,cor_id:d.cor_id?Number(d.cor_id):null};const r=await api(`/api/veiculos/${veic.id}`,{method:"PUT",body:JSON.stringify(corpo)});$("#modal-root").innerHTML="";toast(r.mensagem);await vehicles();});
        }
        if(alternar){
          const ativar=alternar.dataset.ativo==="1";
          if(!await confirmar(ativar?"Ativar veículo":"Desativar veículo",ativar?"O veículo volta a poder ser usado em contratos.":"O veículo deixa de ser usado em contratos. O histórico é mantido.",ativar?"Ativar":"Desativar",!ativar))return;
          const r=await api(`/api/veiculos/${alternar.dataset.toggle}/ativo`,{method:"POST",body:JSON.stringify({ativo:ativar})});toast(r.mensagem);await vehicles();
        }
      }catch(err){toast(err.message,"error");}
    });
    $("#new-vehicle").onclick=()=>{modal("Cadastrar veículo",`<form id="vehicle-form" class="form-grid">${select("Cliente","cliente_id",clientes.map(c=>({value:c.id??c.cliente_id,label:`${c.nome} · ${fmtDoc(c.documento)}`})))}${select("Tipo de veículo","tipo_veiculo_id",tipos)}${field("Placa","placa","text",true,"ABC1D23",'maxlength="8" autocapitalize="characters"')}${select("Marca (opcional)","marca_id",marcas,false)}${select("Modelo (opcional)","modelo_id",modelos.map(m=>({value:m.id??m.modelo_id,label:m.nome??m.modelo_nome})),false)}${select("Cor (opcional)","cor_id",cores.map(c=>({value:c.id??c.cor_id,label:c.nome??c.cor_nome})),false)}<div class="span-2"><button type="button" class="btn btn-secondary btn-sm" data-quick="marcas">＋ Nova marca</button> <button type="button" class="btn btn-secondary btn-sm" data-quick="modelos">＋ Novo modelo</button> <button type="button" class="btn btn-secondary btn-sm" data-quick="cores">＋ Nova cor</button></div><div class="span-2" id="quick-row" style="display:none;gap:8px;align-items:center"><input id="quick-name" maxlength="60" placeholder="Nome"><button type="button" class="btn btn-primary btn-sm" id="quick-save">Salvar</button><button type="button" class="btn btn-secondary btn-sm" id="quick-cancel">Cancelar</button></div><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar veículo</button></div></form>`);
    {const marSel=$('#vehicle-form [name="marca_id"]'),modSel=$('#vehicle-form [name="modelo_id"]'),corSel=$('#vehicle-form [name="cor_id"]');let quickKey=null;const row=$("#quick-row"),nameEl=$("#quick-name");
    const fillModelos=keep=>{const mid=marSel.value;const temMarca=modelos.some(m=>m.marca_id!=null);const lista=mid&&temMarca?modelos.filter(m=>String(m.marca_id)===mid):modelos;modSel.innerHTML='<option value="">Selecione...</option>'+lista.map(m=>`<option value="${esc(m.id)}">${esc(m.nome)}</option>`).join("");if(keep)modSel.value=keep;};
    marSel.addEventListener("change",()=>fillModelos());
    const dicas={marcas:"Nome da marca",modelos:"Nome do modelo (da marca escolhida acima)",cores:"Nome da cor"};
    $$("[data-quick]").forEach(b=>b.addEventListener("click",()=>{quickKey=b.dataset.quick;row.style.display="flex";nameEl.placeholder=dicas[quickKey];nameEl.value="";nameEl.focus();}));
    $("#quick-cancel").onclick=()=>{row.style.display="none";quickKey=null;};
    const salvarRapido=async()=>{try{const nome=nameEl.value.trim();if(!quickKey||!nome){toast("Digite o nome.","error");return;}const body={nome};if(quickKey==="modelos"){if(!marSel.value){toast("Escolha a marca antes de cadastrar o modelo.","error");return;}body.marca_id=Number(marSel.value);}
      const r=await api(`/api/catalogos/${quickKey}`,{method:"POST",body:JSON.stringify(body)});
      if(quickKey==="marcas"){marcas.push({id:r.id,nome});const o=document.createElement("option");o.value=r.id;o.textContent=nome;marSel.append(o);marSel.value=r.id;fillModelos();}
      else if(quickKey==="modelos"){modelos.push({id:r.id,nome,marca_id:body.marca_id});fillModelos(String(r.id));}
      else{const o=document.createElement("option");o.value=r.id;o.textContent=nome;corSel.append(o);corSel.value=r.id;}
      row.style.display="none";quickKey=null;toast("Cadastrado com sucesso.");}catch(err){toast(err.message||"Erro inesperado.","error");}};
    $("#quick-save").onclick=salvarRapido;nameEl.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();salvarRapido();}});}
    catchForm($("#vehicle-form"),async e=>{const d=fd(e.currentTarget);delete d.marca_id;d.placa=d.placa.toUpperCase().replace(/[^A-Z0-9]/g,"");["cliente_id","tipo_veiculo_id","modelo_id","cor_id"].forEach(k=>{if(d[k])d[k]=Number(d[k]);else delete d[k];});await api("/api/veiculos",{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Veículo cadastrado.");await vehicles();});};
  }

  P.telas.veiculos = vehicles;
})();
