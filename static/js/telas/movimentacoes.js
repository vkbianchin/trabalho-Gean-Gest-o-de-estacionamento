/* Tela: movimentacoes */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, money, dt, date, toast, api, fd, field, select, table, panel, cpfValido, cnpjValido, permanencia, modal, catchForm, badge, pedirMotivo, ehAdmin } = P;
  const $ = P.$;
  const $$ = P.$$;

  async function movements(){
    const root=$("#app-content");
    const [movs,tipos,vagas,caixa]=await Promise.all([api("/api/movimentacoes"),api("/api/catalogos/tipos_veiculo"),api("/api/vagas"),api("/api/caixa")]);
    let precoCache=null,consultaEntrada=0,consultaSaida=0;
    const open=movs.filter(m=>!m.saida_em&&!Number(m.cancelada));
    const livres=vagas.filter(v=>!Number(v.ocupada)&&Number(v.ativo)!==0);
    const opcoesVaga=livres.map(v=>`<option value="${esc(v.id)}" data-tipo="${esc(v.tipo_veiculo_id)}">Vaga ${esc(v.numero)} · ${esc(v.tipo_veiculo)} · ${esc(v.plano)}</option>`).join("");
    const placaLink=v=>`<a href="/historico?placa=${encodeURIComponent(v)}">${esc(v)}</a>`;
    root.innerHTML=`<div class="notice notice-info">Digite a placa: o sistema mostra se o veículo já está no local, o tempo de permanência e o valor antes de você confirmar.</div>
    <div class="columns-2"><div>${panel("Registrar entrada","Use para veículos ainda não registrados no estacionamento",`<form id="entry-form" class="form-grid">
      <label class="span-2">Placa do veículo<input name="placa" required maxlength="8" placeholder="ABC1D23" autocapitalize="characters" autocomplete="off"></label>
      <div id="entry-info" class="notice notice-info span-2" hidden></div>
      ${select("Tipo de veículo","tipo_veiculo_id",tipos)}
      <label>Vaga (opcional)<select name="vaga_id"><option value="">Escolher automaticamente</option>${opcoesVaga}</select></label>
      <div id="price-warning" class="notice notice-warning span-2" hidden></div>
      <div class="form-actions span-2"><button class="btn btn-primary">Registrar entrada →</button></div></form>`)}</div>
    <div>${panel("Registrar saída","Mostra a permanência e o valor antes de confirmar",`<form id="exit-form" class="form-stack">
      ${field("Placa do veículo","placa","text",true,"ABC1D23",'maxlength="8" autocapitalize="characters" autocomplete="off"')}
      <div id="exit-preview" class="exit-preview" hidden></div>
      <div id="exit-payment" class="form-stack" hidden>
        <label>Forma de pagamento<select name="forma_pagamento"><option value="dinheiro">Dinheiro</option><option value="pix">Pix</option><option value="cartao_debito">Cartão de débito</option><option value="cartao_credito">Cartão de crédito</option></select></label>
        <label>CPF/CNPJ no recibo (opcional)<input name="documento_recibo" placeholder="Somente se o cliente pedir" maxlength="18" inputmode="numeric"></label>
        <div class="notice ${caixa.aberto?"notice-success":"notice-warning"}">${caixa.aberto?"Caixa aberto. Recebimentos liberados.":"Caixa fechado. Abra o caixa antes de receber."}</div>
      </div>
      <button class="btn btn-primary">Registrar saída</button></form>`)}</div></div>
    ${panel("Veículos no estacionamento",`${open.length} movimentação(ões) em aberto`,table([{key:"placa",label:"Placa",render:placaLink},{key:"vaga_numero",label:"Vaga"},{key:"entrada_em",label:"Entrada",render:dt},{key:"plano_id",label:"",render:(v,r)=>`<button class="btn btn-secondary btn-sm" data-exit="${esc(r.placa)}">Dar saída</button>${ehAdmin()?` <button class="btn btn-danger btn-sm" data-cancel-mov="${esc(r.id)}">Cancelar entrada</button>`:""}`}],open,"Nenhum veículo no local."))}
    ${panel("Histórico recente","Movimentações mais recentes",table([{key:"placa",label:"Placa",render:placaLink},{key:"vaga_numero",label:"Vaga"},{key:"entrada_em",label:"Entrada",render:dt},{key:"saida_em",label:"Saída",render:(v,r)=>Number(r.cancelada)?badge("Cancelada"):dt(v)},{key:"saida_em",label:"Permanência",render:(v,r)=>esc(permanencia(r.entrada_em,v))},{key:"valor_cobrado",label:"Valor",render:(v,r)=>r.saida_em&&!Number(r.cancelada)?money(v):"—"}],movs.slice(0,100)))}`;

    const entrada=$("#entry-form"),saida=$("#exit-form"),vagaSel=entrada.elements.vaga_id,tipoSel=entrada.elements.tipo_veiculo_id;
    const normalizar=v=>v.toUpperCase().replace(/[^A-Z0-9]/g,"");
    const placaCompleta=v=>/^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(v);
    // Só mostra as vagas do tipo escolhido (carro ou moto).
    const filtrarVagas=()=>{const tid=tipoSel.value;[...vagaSel.options].forEach(o=>{if(!o.value)return;o.hidden=!!tid&&o.dataset.tipo!==tid;});if(vagaSel.selectedOptions[0]?.hidden)vagaSel.value="";};
    tipoSel.addEventListener("change",filtrarVagas);

    // Consulta da placa na entrada: avisa se já está no local e se é mensalista com mensalidade em atraso.
    entrada.elements.placa.addEventListener("input",async e=>{
      const box=$("#entry-info"),p=normalizar(e.target.value),minha=++consultaEntrada;box.hidden=true;if(!placaCompleta(p))return;
      try{
        const r=await api(`/api/placa/${p}`);if(minha!==consultaEntrada)return;
        let html="",tipo="notice-info";
        if(r.movimentacao_aberta){html=`Este veículo já está no local (vaga ${esc(r.movimentacao_aberta.vaga_numero)}, desde ${dt(r.movimentacao_aberta.entrada_em)}). Registre a saída.`;tipo="notice-warning";}
        else if(r.mensalista){html=`Mensalista: <strong>${esc(r.mensalista.cliente_nome)}</strong>. Contrato vigente.`;tipoSel.value=String(r.mensalista.tipo_veiculo_id);filtrarVagas();
          if(r.mensalista.em_atraso){const a=r.mensalista.em_atraso;html+=`<br>⚠ ${esc(a.quantidade)} mensalidade(s) em atraso (${money(a.total)}), a mais antiga venceu em ${date(a.mais_antigo)}.`;tipo="notice-warning";}}
        else html="Veículo sem contrato: será tratado como horista.";
        box.className=`notice ${tipo} span-2`;box.innerHTML=html;box.hidden=false;
      }catch{}
    });

    // Prévia da saída: permanência, valor e necessidade de pagamento.
    const mostrarPrevia=async p=>{
      const box=$("#exit-preview"),pay=$("#exit-payment"),minha=++consultaSaida;box.hidden=true;pay.hidden=true;if(!placaCompleta(p))return;
      try{
        const r=await api(`/api/saida/previa/${p}`);if(minha!==consultaSaida)return;
        box.className="exit-preview";
        box.innerHTML=`<dl><dt>Vaga</dt><dd>${esc(r.vaga)} · ${esc(r.tipo_veiculo)}</dd><dt>Plano</dt><dd>${esc(r.plano)}</dd><dt>Entrada</dt><dd>${dt(r.entrada_em)}</dd><dt>Saída (agora)</dt><dd>${dt(r.saida_em)}</dd><dt>Tempo estacionado</dt><dd><strong>${esc(r.tempo)}</strong></dd><dt>Tolerância</dt><dd>${esc(r.tolerancia_minutos)} min</dd><dt>Valor a cobrar</dt><dd><strong>${r.mensalista?"Mensalista — sem cobrança":money(r.valor)}</strong></dd></dl>`;
        box.hidden=false;pay.hidden=!r.exige_pagamento;
      }catch(err){if(minha!==consultaSaida)return;box.className="exit-preview exit-preview-erro";box.textContent=err.message;box.hidden=false;}
    };
    saida.elements.placa.addEventListener("input",e=>mostrarPrevia(normalizar(e.target.value)));
    // Cancelar uma entrada lançada por engano (só administrador): libera a vaga e registra o motivo.
    $$("[data-cancel-mov]").forEach(b=>b.addEventListener("click",async()=>{
      const motivo=await pedirMotivo("Cancelar entrada","A vaga será liberada e a passagem ficará marcada como cancelada, fora de relatórios e financeiro.","Cancelar entrada");
      if(!motivo)return;
      try{const r=await api(`/api/movimentacoes/${b.dataset.cancelMov}/cancelar`,{method:"POST",body:JSON.stringify({motivo})});toast(r.mensagem);await movements();}catch(e){toast(e.message,"error");}
    }));
    $$("[data-exit]").forEach(b=>b.addEventListener("click",()=>{saida.elements.placa.value=b.dataset.exit;saida.elements.placa.dispatchEvent(new Event("input"));saida.scrollIntoView({behavior:"smooth",block:"center"});}));

    tipoSel.addEventListener("change",async e=>{const box=$("#price-warning");const tid=Number(e.target.value);if(!tid){box.hidden=true;return;}try{if(!precoCache)precoCache=await Promise.all([api("/api/precos"),api("/api/catalogos/planos")]);}catch{box.hidden=true;return;}const [precos,planos]=precoCache;const horista=planos.find(p=>p.cobranca==="hora");if(!horista){box.hidden=true;return;}const tem=precos.some(x=>Number(x.plano_id)===Number(horista.id)&&Number(x.tipo_veiculo_id)===tid);const nome=e.target.options[e.target.selectedIndex].text;box.textContent=tem?"":`Não há preço do plano ${horista.nome} cadastrado para ${nome}. Se este veículo não for mensalista, a saída não poderá ser calculada. Cadastre em Catálogos > Preços.`;box.hidden=tem;});
    catchForm(entrada,async e=>{const d=fd(e.currentTarget);d.placa=normalizar(d.placa);d.tipo_veiculo_id=Number(d.tipo_veiculo_id);if(d.vaga_id)d.vaga_id=Number(d.vaga_id);else delete d.vaga_id;const r=await api("/api/entrada",{method:"POST",body:JSON.stringify(d)});toast(`Entrada registrada: ${r.placa||d.placa}${r.vaga?` · vaga ${r.vaga}`:""}`);await movements();});
    catchForm(saida,async e=>{
      const d=fd(e.currentTarget);d.placa=normalizar(d.placa);
      const doc=(d.documento_recibo||"").replace(/\D/g,"");delete d.documento_recibo;
      if(doc&&!((doc.length===11&&cpfValido(doc))||(doc.length===14&&cnpjValido(doc))))throw new Error("O CPF/CNPJ informado para o recibo é inválido.");
      if($("#exit-payment").hidden)delete d.forma_pagamento;
      const r=await api("/api/saida",{method:"POST",body:JSON.stringify(d)});
      await movements();resumoSaida(r,doc);
    });
  }
  function resumoSaida(r,doc){
    const rotulos={dinheiro:"Dinheiro",pix:"Pix",cartao_debito:"Cartão de débito",cartao_credito:"Cartão de crédito"};
    const recibo=r.pagamento_id?`<a class="btn btn-primary" target="_blank" rel="noopener" href="/recibo/pagamento/${esc(r.pagamento_id)}${doc?`?documento=${encodeURIComponent(doc)}`:""}">Imprimir recibo</a>`:"";
    modal("Saída registrada",`<div class="exit-preview"><dl><dt>Placa</dt><dd>${esc(r.placa)}</dd><dt>Vaga</dt><dd>${esc(r.vaga)}</dd><dt>Entrada</dt><dd>${dt(r.entrada_em)}</dd><dt>Saída</dt><dd>${dt(r.saida_em)}</dd><dt>Tempo total estacionado</dt><dd><strong>${esc(r.tempo)}</strong></dd><dt>Valor cobrado</dt><dd><strong>${r.mensalista?"Mensalista — sem cobrança":money(r.valor)}</strong></dd>${r.forma_pagamento?`<dt>Forma de pagamento</dt><dd>${esc(rotulos[r.forma_pagamento]||r.forma_pagamento)}</dd>`:""}</dl></div><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Fechar</button>${recibo}</div>`);
  }

  P.telas.movimentacoes = movements;
})();
