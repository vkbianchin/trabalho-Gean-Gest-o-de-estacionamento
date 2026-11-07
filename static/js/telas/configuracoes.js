/* Tela: configuracoes */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, toast, api, fd, field, select, panel, fmtDoc, catchForm } = P;
  const $ = P.$;

  async function settings(){
    const c=await api("/api/configuracoes");
    $("#app-content").innerHTML=panel("Configurações do estacionamento","Regras de cobrança e dados que aparecem no recibo. Os preços ficam em Catálogos > Preços.",`<form id="settings-form" class="form-grid content-narrow">
      <h3 class="span-2">Regras de cobrança</h3>
      ${field("Nome do estacionamento","nome_estacionamento","text",true,"Nome do estacionamento",'maxlength="80" value="'+esc(c.nome_estacionamento||"")+'"')}
      ${field("Tolerância (minutos)","tolerancia_minutos","number",true,"10",'min="0" max="1440" value="'+esc(c.tolerancia_minutos??10)+'"')}
      ${field("Fração de cobrança (minutos)","fracao_minutos","number",true,"30",'min="1" max="60" value="'+esc(c.fracao_minutos??30)+'"')}
      <label>Regra de arredondamento<select name="arredondamento"><option value="fracao" ${c.arredondamento==="fracao"?"selected":""}>Por fração de tempo</option><option value="hora_cheia" ${c.arredondamento==="hora_cheia"?"selected":""}>Hora cheia</option></select></label>
      ${field("Carência para atraso (dias)","dias_carencia_atraso","number",true,"0",'min="0" max="30" value="'+esc(c.dias_carencia_atraso??0)+'"')}
      <small class="span-2">Uma mensalidade só conta como em atraso depois do vencimento mais a carência.</small>
      <h3 class="span-2">Dados para o recibo</h3>
      ${field("Razão social","razao_social","text",false,"Opcional",'maxlength="150" value="'+esc(c.razao_social||"")+'"')}
      ${field("CNPJ","cnpj","text",false,"00.000.000/0000-00",'maxlength="18" inputmode="numeric" value="'+esc(fmtDoc(c.cnpj)==="—"?"":fmtDoc(c.cnpj))+'"')}
      ${field("Endereço","endereco","text",false,"Rua, número, cidade",'maxlength="200" value="'+esc(c.endereco||"")+'"')}
      ${field("Telefone","telefone","tel",false,"(00) 00000-0000",'value="'+esc(c.telefone||"")+'"')}
      <div class="form-actions span-2"><button class="btn btn-primary">Salvar configurações</button></div></form>`);
    catchForm($("#settings-form"),async e=>{
      const d=fd(e.currentTarget);["tolerancia_minutos","fracao_minutos","dias_carencia_atraso"].forEach(k=>d[k]=Number(d[k]));
      d.cnpj=(d.cnpj||"").replace(/\D/g,"");d.telefone=(d.telefone||"").replace(/\D/g,"");
      const r=await api("/api/configuracoes",{method:"PUT",body:JSON.stringify(d)});
      toast(r.campos_ignorados?.length?"Configurações salvas. Aplique a migração 004 para gravar os dados do recibo e a carência.":"Configurações atualizadas.");
    });
  }

  P.telas.configuracoes = settings;
})();
