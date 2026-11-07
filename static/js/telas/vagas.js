/* Tela: vagas */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, toast, api, fd, field, select, badge, table, stat, panel, modal, catchForm, confirmar, ehAdmin } = P;
  const $ = P.$;
  const $$ = P.$$;

  const tipoClasse=t=>String(t||"").toLowerCase()==="moto"?"badge-amber":"badge-blue";
  async function vacancies(){
    const [rows,tipos,planos]=await Promise.all([api("/api/vagas"),api("/api/catalogos/tipos_veiculo"),api("/api/catalogos/planos")]);const occ=rows.filter(v=>Number(v.ocupada)===1||v.ocupada===true).length;
    $("#app-content").innerHTML=`<div class="stats-grid">${stat("Total de vagas",rows.length,"▦","Vagas cadastradas")}${stat("Ocupadas",occ,"▰","Em uso agora")}${stat("Livres",rows.length-occ,"✓","Disponíveis")}${stat("Ocupação",rows.length?Math.round(occ/rows.length*100)+"%":"0%","◔","Percentual de ocupação")}</div>${panel("Mapa de vagas","A ocupação é calculada pelas movimentações abertas.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar número, tipo ou plano..."></label><select class="field" id="vacancy-filter"><option value="">Todas as vagas</option><option value="livre">Somente livres</option><option value="ocupada">Somente ocupadas</option><option value="inativa">Somente inativas</option></select><select class="field" id="vacancy-type"><option value="">Carros e motos</option>${(tipos||[]).map(t=>`<option value="${esc(String(t.nome).toLowerCase())}">${esc(t.nome)}</option>`).join("")}</select><button class="btn btn-primary" id="new-vacancy">＋ Nova vaga</button></div><div style="height:15px"></div><div class="vacancy-grid" id="vacancy-grid">${rows.map(v=>{const occupied=Number(v.ocupada)===1||v.ocupada===true;const inativa=Number(v.ativo)===0;const estado=inativa?"inativa":occupied?"ocupada":"livre";const num=v.numero??v.vaga_numero??v.id;return `<article class="vacancy ${inativa?"inactive":occupied?"occupied":"free"}" data-state="${estado}" data-tipo="${esc(String(v.tipo_veiculo||"").toLowerCase())}" data-search="${esc(`${num} ${v.tipo_veiculo||""} ${v.plano||""}`.toLocaleLowerCase("pt-BR"))}"><span class="vacancy-icon">▰</span><strong>${esc(num)}</strong><span class="badge ${tipoClasse(v.tipo_veiculo)}">${esc(v.tipo_veiculo)}</span><small>${esc(v.plano)}</small>${badge(inativa?"Inativa":occupied?"Ocupada":"Livre")}${ehAdmin()?`<span class="vacancy-actions"><button class="btn btn-secondary btn-sm" data-edit="${esc(v.id)}">Editar</button><button class="btn ${inativa?"btn-secondary":"btn-danger"} btn-sm" data-toggle="${esc(v.id)}" data-ativo="${inativa?1:0}">${inativa?"Ativar":"Desativar"}</button></span>`:""}</article>`}).join("")||'<div class="empty-row">Nenhuma vaga cadastrada.</div>'}</div>`)}`;
    const filter=()=>{const q=$("#search-table").value.toLocaleLowerCase("pt-BR"),est=$("#vacancy-filter").value,tp=$("#vacancy-type").value;$$(".vacancy").forEach(el=>el.hidden=!(el.dataset.search.includes(q)&&(!est||el.dataset.state===est)&&(!tp||el.dataset.tipo===tp)));};
    $("#search-table").addEventListener("input",filter);$("#vacancy-filter").addEventListener("change",filter);$("#vacancy-type").addEventListener("change",filter);
    // Editar número, tipo e plano (a vaga não pode estar ocupada) e ativar/desativar. Só administrador vê os botões.
    $("#vacancy-grid").addEventListener("click",async e=>{
      const editar=e.target.closest("[data-edit]"),alternar=e.target.closest("[data-toggle]");
      try{
        if(editar){
          const v=rows.find(x=>String(x.id)===editar.dataset.edit);
          modal(`Editar vaga ${v.numero}`,`<form id="vacancy-edit-form" class="form-grid">${field("Número da vaga","numero","number",true,"",`min="1" max="9999" value="${esc(v.numero)}"`)}${select("Tipo de veículo","tipo_veiculo_id",tipos)}${select("Plano","plano_id",planos.filter(p=>Number(p.ativo)===1||Number(p.id)===Number(v.plano_id)))}<small class="span-2">Tipo e plano só podem ser trocados com a vaga livre.</small><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar alterações</button></div></form>`);
          const form=$("#vacancy-edit-form");form.elements.tipo_veiculo_id.value=v.tipo_veiculo_id;form.elements.plano_id.value=v.plano_id;
          catchForm(form,async ev=>{const d=fd(ev.currentTarget);["numero","tipo_veiculo_id","plano_id"].forEach(k=>d[k]=Number(d[k]));const r=await api(`/api/vagas/${v.id}`,{method:"PUT",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast(r.mensagem);await vacancies();});
        }
        if(alternar){
          const ativar=alternar.dataset.ativo==="1";
          if(!await confirmar(ativar?"Ativar vaga":"Desativar vaga",ativar?"A vaga volta a receber veículos.":"A vaga deixa de receber veículos. O histórico é mantido.",ativar?"Ativar":"Desativar",!ativar))return;
          const r=await api(`/api/vagas/${alternar.dataset.toggle}/ativo`,{method:"POST",body:JSON.stringify({ativo:ativar})});toast(r.mensagem);await vacancies();
        }
      }catch(err){toast(err.message,"error");}
    });
    $("#new-vacancy").onclick=()=>{modal("Cadastrar vaga",`<form id="vacancy-form" class="form-grid">${field("Número da vaga","numero","number",true,"Ex.: 1",'min="1" max="9999"')}${select("Tipo de veículo","tipo_veiculo_id",tipos)}${select("Plano","plano_id",planos.filter(p=>Number(p.ativo)===1))}<div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar vaga</button></div></form>`);
    catchForm($("#vacancy-form"),async e=>{const d=fd(e.currentTarget);["numero","tipo_veiculo_id","plano_id"].forEach(k=>d[k]=Number(d[k]));await api("/api/vagas",{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Vaga cadastrada.");await vacancies();});};
  }

  P.telas.vagas = vacancies;
})();
