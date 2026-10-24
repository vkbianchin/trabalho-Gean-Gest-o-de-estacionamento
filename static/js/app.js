(() => {
  "use strict";
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => [...r.querySelectorAll(s)];
  const page = document.body.dataset.page || "";
  let csrfToken = "";
  let user = null;
  const esc = v => String(v ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const money = v => new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(v || 0));
  const dt = v => { if(!v)return "—"; const d=new Date(String(v).replace(" ","T")); return Number.isNaN(d.getTime())?esc(v):d.toLocaleString("pt-BR"); };
  const date = v => { if(!v)return "—"; const d=new Date(String(v).slice(0,10)+"T12:00:00"); return Number.isNaN(d.getTime())?esc(v):d.toLocaleDateString("pt-BR"); };
  function toast(message,type="success"){const root=$("#toast-region");if(!root){alert(message);return;}const el=document.createElement("div");el.className="toast "+type;el.textContent=message;root.append(el);}
  async function api(url,opts={}){
    const options={credentials:"same-origin",...opts};
    options.headers={Accept:"application/json",...(options.body?{"Content-Type":"application/json"}:{}),...(csrfToken?{"X-CSRFToken":csrfToken}:{}),...(options.headers||{})};
    let res;try{res=await fetch(url,options);}catch{throw new Error("Não foi possível conectar ao servidor Flask.");}
    const ct=res.headers.get("content-type")||"";let data=ct.includes("application/json")?await res.json():await res.text();
    if(!res.ok){if(res.status===401&&page!=="login")location.href="/login";throw new Error((data&&(data.mensagem||data.erro||data.message))||"Não foi possível concluir a operação.");}
    return data;
  }
  async function initCsrf(){try{const r=await fetch("/api/csrf",{credentials:"same-origin"});if(r.ok){const d=await r.json();csrfToken=d.csrf_token||"";const m=$('meta[name="csrf-token"]');if(m)m.content=csrfToken;}}catch{}}
  const fd = form => Object.fromEntries(new FormData(form).entries());
  const moneyField = (label,name,required=true,value="") => `<label>${label}<input name="${name}" type="number" min="0" step=".01" ${required?"required":""} value="${esc(value)}"></label>`;
  const field = (label,name,type="text",required=true,placeholder="",extra="") => `<label>${label}<input name="${name}" type="${type}" ${required?"required":""} placeholder="${placeholder}" ${extra}></label>`;
  const select = (label,name,options,required=true) => `<label>${label}<select name="${name}" ${required?"required":""}><option value="">Selecione...</option>${(options||[]).map(o=>`<option value="${esc(o.value??o.id)}">${esc(o.label??o.nome)}</option>`).join("")}</select></label>`;
  function badge(value){const s=String(value??"").toLowerCase();let cls="badge-blue";if(["ativo","pago","aberto","vigente","disponível","disponivel","livre","sim"].includes(s))cls="badge-green";else if(["inativo","cancelado","fechado","encerrado","ocupada","ocupado","não","nao"].includes(s))cls="badge-gray";else if(s.includes("atras")||s.includes("inadimpl")||s.includes("vencid"))cls="badge-red";else if(s.includes("pend")||s.includes("abert"))cls="badge-amber";return `<span class="badge ${cls}">${esc(value)}</span>`;}
  function table(cols,rows,empty="Nenhum registro encontrado."){if(!rows?.length)return `<div class="empty-row">${esc(empty)}</div>`;return `<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th>${esc(c.label)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${c.render?c.render(r[c.key],r):esc(r[c.key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;}
  function stat(label,value,icon,note){return `<article class="stat-card"><div class="stat-top"><span>${esc(label)}</span><span class="stat-icon">${icon}</span></div><div class="stat-number">${esc(value)}</div><div class="stat-note">${esc(note)}</div></article>`;}
  function panel(title,subtitle,body,right=""){return `<section class="panel"><div class="panel-heading"><div><h2>${title}</h2>${subtitle?`<p>${subtitle}</p>`:""}</div>${right}</div>${body}</section>`;}
  function cpfValido(valor){const cpf=String(valor||"").replace(/\D/g,"");if(cpf.length!==11||/^(\d)\1{10}$/.test(cpf))return false;let soma=0;for(let i=0;i<9;i++)soma+=Number(cpf[i])*(10-i);let dig=(soma*10)%11;if(dig===10)dig=0;if(dig!==Number(cpf[9]))return false;soma=0;for(let i=0;i<10;i++)soma+=Number(cpf[i])*(11-i);dig=(soma*10)%11;if(dig===10)dig=0;return dig===Number(cpf[10]);}
  function validationMessage(el){const v=el.value.trim(),name=(el.name||"").toLowerCase(),label=el.closest("label")?.childNodes?.[0]?.textContent?.trim()||el.getAttribute("aria-label")||name||"Este campo";if(!v){return el.required?`${label}: este campo é obrigatório.`:"";}if(name==="cpf"){const digits=v.replace(/\D/g,"");if(digits.length<11)return "Digite os 11 números do CPF.";if(!cpfValido(v))return "CPF inválido. Confira os números digitados.";}if(name==="cep"&&v.replace(/\D/g,"").length!==8)return "CEP deve conter 8 números.";if(name==="telefone"){const n=v.replace(/\D/g,"");if(n.length<10||n.length>11)return "Telefone deve ter DDD e 10 ou 11 números.";}if(el.type==="email"&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))return "Digite um e-mail válido.";if(name==="placa"&&!/^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(v.replace(/[^A-Z0-9]/g,"").toUpperCase()))return "Placa inválida. Use ABC1234 ou ABC1D23.";if(el.type==="number"){const n=Number(v),min=el.min!==""?Number(el.min):null,max=el.max!==""?Number(el.max):null;if(!Number.isFinite(n))return "Digite um número válido.";if(min!==null&&n<min)return `O valor mínimo é ${min}.`;if(max!==null&&n>max)return `O valor máximo é ${max}.`;}if(el.minLength>0&&v.length<el.minLength)return `Digite pelo menos ${el.minLength} caracteres.`;if(el.maxLength>0&&v.length>el.maxLength)return `Digite no máximo ${el.maxLength} caracteres.`;return "";}
  function validateField(el,show=true){if(!el||el.disabled||["submit","button","reset","hidden"].includes(el.type))return true;const msg=validationMessage(el);el.setAttribute("aria-invalid",msg?"true":"false");let hint=el.parentElement?.querySelector(`.live-field-error[data-for="${CSS.escape(el.name||el.id||"")}"]`);if(!hint&&el.parentElement){hint=document.createElement("small");hint.className="live-field-error";hint.dataset.for=el.name||el.id||"";hint.setAttribute("aria-live","polite");el.insertAdjacentElement("afterend",hint);}if(hint){hint.textContent=show?msg:"";hint.hidden=!show||!msg;}return !msg;}
  function enableLiveValidation(form){if(!form||form.dataset.liveValidation==="true")return;form.dataset.liveValidation="true";const touched=new WeakSet();form.querySelectorAll("input,select,textarea").forEach(el=>{el.addEventListener("input",()=>{touched.add(el);if(el.name==="cpf"){let n=el.value.replace(/\D/g,"").slice(0,11);el.value=n.replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d{1,2})$/,"$1-$2");}else if(el.name==="cep"){let n=el.value.replace(/\D/g,"").slice(0,8);el.value=n.length>5?n.slice(0,5)+"-"+n.slice(5):n;}else if(el.name==="telefone"){let n=el.value.replace(/\D/g,"").slice(0,11);if(n.length>10)el.value=n.replace(/(\d{2})(\d{5})(\d{4})/,"($1) $2-$3");else if(n.length>6)el.value=n.replace(/(\d{2})(\d{4})(\d{0,4})/,"($1) $2-$3");else if(n.length>2)el.value=n.replace(/(\d{2})(\d+)/,"($1) $2");else el.value=n;}else if(el.name==="placa")el.value=el.value.toUpperCase().replace(/[^A-Z0-9]/g,"").slice(0,7);validateField(el,true);});el.addEventListener("blur",()=>{touched.add(el);validateField(el,true);});});form.addEventListener("submit",e=>{let first=null;form.querySelectorAll("input,select,textarea").forEach(el=>{if(!validateField(el,true)&&!first)first=el;});if(first){e.preventDefault();e.stopImmediatePropagation();first.focus();}} ,true);}
  function modal(title,body){const root=$("#modal-root");root.innerHTML=`<div class="modal-backdrop" data-backdrop><section class="modal" role="dialog" aria-modal="true"><div class="modal-header"><h2>${esc(title)}</h2><button type="button" class="modal-close" data-close>×</button></div><div class="modal-body">${body}</div></section></div>`;root.querySelectorAll("form").forEach(enableLiveValidation);root.querySelector("[data-backdrop]").addEventListener("click",e=>{if(e.target.matches("[data-backdrop]")||e.target.closest("[data-close]"))root.innerHTML="";});root.querySelector(".modal").addEventListener("click",e=>e.stopPropagation());}
  function catchForm(form,fn){if(!form)return;enableLiveValidation(form);form.addEventListener("submit",async e=>{e.preventDefault();const b=form.querySelector('[type="submit"]');if(b)b.disabled=true;try{await fn(e); }catch(err){toast(err.message||"Erro inesperado.","error");}finally{if(b)b.disabled=false;}});}
  function wireSearch(input,root){input?.addEventListener("input",()=>{const q=input.value.toLocaleLowerCase("pt-BR");root?.querySelectorAll("tbody tr").forEach(tr=>tr.hidden=!tr.textContent.toLocaleLowerCase("pt-BR").includes(q));root?.querySelectorAll(".vacancy").forEach(el=>el.hidden=!el.dataset.search.includes(q));});}
  function go(url){location.href=url;}
  async function loadUser(){
    try{user=await api("/api/sessao");$("#user-name").textContent=user.nome||user.login||"Usuário";$("#user-role").textContent=user.nivel_acesso==="administrador"?"Administrador":"Operador";$("#user-avatar").textContent=(user.nome||"U").trim().charAt(0).toUpperCase();
      if(user.trocar_senha&&page!=="trocar_senha")go("/trocar-senha");
      if(user.nivel_acesso!=="administrador"){$$(".admin-nav,.admin-nav-label").forEach(el=>el.hidden=true);}
      applyAppearance(user.preferencias || {});

    }catch{}
  }
  function setupShell(){
    const navPage=page==="painel"?"painel":page;
    $$("[data-nav]").forEach(a=>a.classList.toggle("active",a.dataset.nav===navPage));
    const d=$("#today-date");if(d)d.textContent=new Date().toLocaleDateString("pt-BR",{weekday:"short",day:"2-digit",month:"short"});
    $("#mobile-menu")?.addEventListener("click",()=>$("#sidebar")?.classList.toggle("open"));
    $("#account-menu-button")?.addEventListener("click",()=>{const m=$("#account-menu");m.hidden=!m.hidden;});
    $("#logout-button")?.addEventListener("click",async()=>{try{await api("/api/logout",{method:"POST",body:JSON.stringify({})});go("/login");}catch(e){toast(e.message,"error");}});
    $("#settings-shortcut")?.addEventListener("click",()=>{
      const prefs=user?.preferencias||{};
      modal("Ajustes de aparência",`<form id="appearance-form" class="form-stack">
        <label>Tema<select name="tema"><option value="escuro" ${prefs.tema!=="claro"?"selected":""}>Escuro</option><option value="claro" ${prefs.tema==="claro"?"selected":""}>Claro</option></select></label>
        <label>Tamanho do texto<select name="tamanho_texto"><option value="normal" ${prefs.tamanho_texto!=="grande"?"selected":""}>Normal</option><option value="grande" ${prefs.tamanho_texto==="grande"?"selected":""}>Grande</option></select></label>
        <label>Cor de destaque<select name="cor_destaque"><option value="azul" ${!prefs.cor_destaque||prefs.cor_destaque==="azul"?"selected":""}>Azul</option><option value="verde" ${prefs.cor_destaque==="verde"?"selected":""}>Verde</option><option value="violeta" ${prefs.cor_destaque==="violeta"?"selected":""}>Violeta</option><option value="dourado" ${prefs.cor_destaque==="dourado"?"selected":""}>Dourado</option></select></label>
        <label>Sons<select name="sons"><option value="ligados" ${prefs.sons!=="desligados"?"selected":""}>Ligados</option><option value="desligados" ${prefs.sons==="desligados"?"selected":""}>Desligados</option></select></label>
        <div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button type="submit" class="btn btn-primary">Aplicar modificações</button></div>
      </form>`);
      appearance();
    });
    $("#cash-indicator")?.addEventListener("click",()=>go("/caixa"));
  }
  async function updateCashIndicator(){try{const c=await api("/api/caixa");const el=$("#cash-indicator");if(el){el.classList.toggle("open",!!c.aberto);el.innerHTML=`<i></i>${c.aberto?"Caixa aberto":"Caixa fechado"}`;}}catch{}}
  async function dashboard(){
    const root=$("#app-content");const [vagas,movs,caixa]=await Promise.all([api("/api/vagas"),api("/api/movimentacoes"),api("/api/caixa")]);
    const open=movs.filter(m=>m.aberta===true||Number(m.aberta)===1||!m.saida_em&&m.entrada_em);const occupied=vagas.filter(v=>v.ocupada===true||Number(v.ocupada)===1).length;
    root.innerHTML=`<div class="welcome-card"><div><span class="eyebrow">VISÃO GERAL</span><h2>Operação do estacionamento</h2><p>Acompanhe a ocupação e registre movimentos pela placa.</p></div><div class="welcome-icon">▤</div></div><div class="stats-grid">${stat("Vagas cadastradas",vagas.length,"▦","Total configurado")}${stat("Vagas livres",Math.max(0,vagas.length-occupied),"✓","Disponibilidade atual")}${stat("Vagas ocupadas",occupied,"▰","Ocupação atual")}${stat("Veículos no local",open.length,"↕","Movimentações abertas")}</div><div class="columns-2"><div>${panel("Movimentações abertas","Veículos que ainda estão no estacionamento",table([{key:"placa",label:"Placa"},{key:"vaga_numero",label:"Vaga"},{key:"entrada_em",label:"Entrada",render:dt}],open.slice(0,8),"Nenhum veículo estacionado."),`<a class="btn btn-secondary btn-sm" href="/movimentacoes">Ver todas →</a>`)}</div><div>${panel("Acesso rápido","Atalhos para tarefas do turno",`<div class="quick-actions"><button class="quick-action" data-go="/movimentacoes">↕<strong>Entrada / saída</strong><small>Registrar movimento de veículo</small></button><button class="quick-action" data-go="/caixa">＄<strong>Controle de caixa</strong><small>Abrir ou fechar o caixa</small></button><button class="quick-action" data-go="/clientes">♙<strong>Cadastrar cliente</strong><small>Dados dos mensalistas</small></button><button class="quick-action" data-go="/pagamentos">◉<strong>Mensalidades</strong><small>Consultar cobranças</small></button></div>`)}</div></div>`;
    $$("[data-go]").forEach(b=>b.addEventListener("click",()=>go(b.dataset.go)));
    if(!caixa.aberto)toast("O caixa está fechado. Abra-o antes de receber pagamentos.","error");
  }
  async function movements(){
    const root=$("#app-content");const [movs,tipos,vagas,caixa]=await Promise.all([api("/api/movimentacoes"),api("/api/catalogos/tipos_veiculo"),api("/api/vagas"),api("/api/caixa")]);let precoCache=null;
    const open=movs.filter(m=>m.aberta===true||Number(m.aberta)===1||(!m.saida_em&&m.entrada_em));
    root.innerHTML=`<div class="notice notice-info">Digite a placa para consultar o veículo. O backend deve decidir se a operação é entrada ou saída e validar as regras de mensalista/horista.</div><div class="columns-2"><div>${panel("Registrar entrada","Use para veículos ainda não registrados no estacionamento",`<form id="entry-form" class="form-grid"><label class="span-2">Placa do veículo<input name="placa" required maxlength="8" placeholder="ABC1D23" autocapitalize="characters"></label>${select("Tipo de veículo","tipo_veiculo_id",tipos)}<label>Vaga (opcional)<select name="vaga_id"><option value="">Escolher automaticamente</option>${vagas.filter(v=>!Number(v.ocupada)).map(v=>`<option value="${esc(v.id??v.vaga_id)}">${esc(v.numero??v.vaga_numero)} · ${esc(v.tipo_veiculo)} · ${esc(v.plano)}</option>`).join("")}</select></label><div id="price-warning" class="notice notice-warning span-2" hidden></div><div class="form-actions span-2"><button class="btn btn-primary">Registrar entrada →</button></div></form>`)}</div><div>${panel("Registrar saída","Horistas precisam de caixa aberto para pagar",`<form id="exit-form" class="form-stack">${field("Placa do veículo","placa","text",true,"ABC1D23",'maxlength="8" autocapitalize="characters"')}<label>Forma de pagamento<select name="forma_pagamento"><option value="dinheiro">Dinheiro</option><option value="pix">Pix</option><option value="cartao_debito">Cartão de débito</option><option value="cartao_credito">Cartão de crédito</option></select></label><div class="notice ${caixa.aberto?"notice-success":"notice-warning"}">${caixa.aberto?"Caixa aberto. Recebimentos liberados.":"Caixa fechado. Abra o caixa antes de receber."}</div><button class="btn btn-primary">Calcular e registrar saída</button></form>`)}</div></div>${panel("Veículos no estacionamento",`${open.length} movimentação(ões) em aberto`,table([{key:"placa",label:"Placa"},{key:"vaga_numero",label:"Vaga"},{key:"entrada_em",label:"Entrada",render:dt},{key:"plano",label:"Plano"}],open,"Nenhum veículo no local."))}${panel("Histórico recente","Movimentações mais recentes",table([{key:"placa",label:"Placa"},{key:"vaga_numero",label:"Vaga"},{key:"entrada_em",label:"Entrada",render:dt},{key:"saida_em",label:"Saída",render:dt},{key:"valor_cobrado",label:"Valor",render:money}],movs.slice(0,100)))}`;
    $('#entry-form [name="tipo_veiculo_id"]').addEventListener("change",async e=>{const box=$("#price-warning");const tid=Number(e.target.value);if(!tid){box.hidden=true;return;}try{if(!precoCache)precoCache=await Promise.all([api("/api/precos"),api("/api/catalogos/planos")]);}catch{box.hidden=true;return;}const [precos,planos]=precoCache;const horista=planos.find(p=>p.cobranca==="hora");if(!horista){box.hidden=true;return;}const tem=precos.some(x=>Number(x.plano_id)===Number(horista.id)&&Number(x.tipo_veiculo_id)===tid);const nome=e.target.options[e.target.selectedIndex].text;box.textContent=tem?"":`Não há preço do plano ${horista.nome} cadastrado para ${nome}. Se este veículo não for mensalista, a saída não poderá ser calculada. Cadastre em Catálogos > Preços.`;box.hidden=tem;});
    catchForm($("#entry-form"),async e=>{const d=fd(e.currentTarget);d.placa=d.placa.toUpperCase().replace(/[^A-Z0-9]/g,"");d.tipo_veiculo_id=Number(d.tipo_veiculo_id);if(d.vaga_id)d.vaga_id=Number(d.vaga_id);else delete d.vaga_id;const r=await api("/api/entrada",{method:"POST",body:JSON.stringify(d)});toast(`Entrada registrada: ${r.placa||d.placa}${r.vaga?` · vaga ${r.vaga}`:""}`);await movements();});
    catchForm($("#exit-form"),async e=>{const d=fd(e.currentTarget);d.placa=d.placa.toUpperCase().replace(/[^A-Z0-9]/g,"");const r=await api("/api/saida",{method:"POST",body:JSON.stringify(d)});toast(`Saída registrada. Valor: ${money(r.valor)}`);await movements();});
  }
  async function cash(){
    const root=$("#app-content"),c=await api("/api/caixa");
    if(!c.aberto){root.innerHTML=panel("Abrir caixa","Informe o troco inicial para começar o turno.",`<form id="open-cash" class="form-stack content-narrow">${moneyField("Troco inicial (R$)","valor_inicial",true,"0.00")}<div class="notice notice-info">O caixa precisa estar aberto para receber pagamentos. A operação de entrada de veículos continua disponível.</div><button class="btn btn-primary">Abrir caixa</button></form>`);catchForm($("#open-cash"),async e=>{await api("/api/caixa/abrir",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});toast("Caixa aberto.");await cash();await updateCashIndicator();});return;}
    root.innerHTML=`<div class="stats-grid">${stat("Situação","Aberto","✓","Caixa deste turno")}${stat("Troco inicial",money(c.valor_inicial),"＄","Valor informado na abertura")}${stat("Dinheiro esperado",money(c.dinheiro_esperado),"◉","Troco + pagamentos em dinheiro")}${stat("Identificação",c.id??c.caixa_id??"Atual","▤","Número do caixa")}</div>${panel("Fechar caixa","Conte o dinheiro físico. O sistema calcula a diferença.",`<form id="close-cash" class="form-grid"><label>Dinheiro contado (R$)<input name="dinheiro_contado" type="number" min="0" step=".01" required></label>${field("Observação (opcional)","observacao","text",false,"Observações do fechamento",'maxlength="250"')}<div class="form-actions span-2"><button class="btn btn-danger">Fechar caixa</button></div></form>`)}`;
    catchForm($("#close-cash"),async e=>{if(!confirm("Confirma o fechamento do caixa?"))return;const r=await api("/api/caixa/fechar",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});toast(r.diferenca!==undefined?`Caixa fechado. Diferença: ${money(r.diferenca)}`:"Caixa fechado.");await cash();await updateCashIndicator();});
  }
  async function clients(){
    const rows=await api("/api/clientes"),root=$("#app-content");
    root.innerHTML=panel("Clientes mensalistas","Cadastro e consulta de clientes",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar nome, CPF ou cidade..."></label><button class="btn btn-primary" id="new-client">＋ Novo cliente</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"nome",label:"Nome"},{key:"cpf",label:"CPF"},{key:"telefone",label:"Telefone"},{key:"email",label:"E-mail"},{key:"cidade",label:"Cidade"},{key:"ativo",label:"Status",render:badge}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $("#new-client").onclick=()=>{modal("Cadastrar cliente",`<form id="client-form" class="form-grid">${field("Nome completo","nome")}${field("CPF","cpf","text",true,"000.000.000-00",'maxlength="14"')}${field("Telefone","telefone","tel",true,"(00) 00000-0000")}${field("E-mail (opcional)","email","email",false,"cliente@exemplo.com")}${field("CEP","cep","text",true,"00000-000",'maxlength="9"')}${field("Logradouro","logradouro")}${field("Número","numero")}${field("Complemento (opcional)","complemento","text",false,"Apto, bloco...")}${field("Bairro","bairro")}${field("Cidade","cidade")}<label>UF<select name="uf" required><option value="">Selecione...</option>${["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"].map(x=>`<option ${x==="SC"?"selected":""}>${x}</option>`).join("")}</select></label><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar cliente</button></div></form>`);
    catchForm($("#client-form"),async e=>{await api("/api/clientes",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Cliente cadastrado.");await clients();});};
  }
  async function vehicles(){
    const [rows,clientes,tipos,modelos,cores,marcas]=await Promise.all([api("/api/veiculos"),api("/api/clientes"),api("/api/catalogos/tipos_veiculo"),api("/api/catalogos/modelos"),api("/api/catalogos/cores"),api("/api/catalogos/marcas")]);
    $("#app-content").innerHTML=panel("Veículos cadastrados","Cada veículo mensalista deve estar vinculado a um cliente",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar placa, cliente ou modelo..."></label><button class="btn btn-primary" id="new-vehicle">＋ Novo veículo</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"placa",label:"Placa"},{key:"cliente_nome",label:"Cliente"},{key:"tipo_veiculo",label:"Tipo"},{key:"modelo",label:"Modelo"},{key:"cor",label:"Cor"},{key:"ativo",label:"Status",render:badge}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $("#new-vehicle").onclick=()=>{modal("Cadastrar veículo",`<form id="vehicle-form" class="form-grid">${select("Cliente","cliente_id",clientes.map(c=>({value:c.id??c.cliente_id,label:`${c.nome} · ${c.cpf||""}`})))}${select("Tipo de veículo","tipo_veiculo_id",tipos)}${field("Placa","placa","text",true,"ABC1D23",'maxlength="8" autocapitalize="characters"')}${select("Marca (opcional)","marca_id",marcas,false)}${select("Modelo (opcional)","modelo_id",modelos.map(m=>({value:m.id??m.modelo_id,label:m.nome??m.modelo_nome})),false)}${select("Cor (opcional)","cor_id",cores.map(c=>({value:c.id??c.cor_id,label:c.nome??c.cor_nome})),false)}<div class="span-2"><button type="button" class="btn btn-secondary btn-sm" data-quick="marcas">＋ Nova marca</button> <button type="button" class="btn btn-secondary btn-sm" data-quick="modelos">＋ Novo modelo</button> <button type="button" class="btn btn-secondary btn-sm" data-quick="cores">＋ Nova cor</button></div><div class="span-2" id="quick-row" style="display:none;gap:8px;align-items:center"><input id="quick-name" maxlength="60" placeholder="Nome"><button type="button" class="btn btn-primary btn-sm" id="quick-save">Salvar</button><button type="button" class="btn btn-secondary btn-sm" id="quick-cancel">Cancelar</button></div><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar veículo</button></div></form>`);
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
  async function vacancies(){
    const [rows,tipos,planos]=await Promise.all([api("/api/vagas"),api("/api/catalogos/tipos_veiculo"),api("/api/catalogos/planos")]);const occ=rows.filter(v=>Number(v.ocupada)===1||v.ocupada===true).length;
    $("#app-content").innerHTML=`<div class="stats-grid">${stat("Total de vagas",rows.length,"▦","Vagas cadastradas")}${stat("Ocupadas",occ,"▰","Em uso agora")}${stat("Livres",rows.length-occ,"✓","Disponíveis")}${stat("Ocupação",rows.length?Math.round(occ/rows.length*100)+"%":"0%","◔","Percentual de ocupação")}</div>${panel("Mapa de vagas","A ocupação é calculada pelas movimentações abertas.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar número, tipo ou plano..."></label><select class="field" id="vacancy-filter"><option value="">Todas as vagas</option><option value="livre">Somente livres</option><option value="ocupada">Somente ocupadas</option></select><button class="btn btn-primary" id="new-vacancy">＋ Nova vaga</button></div><div style="height:15px"></div><div class="vacancy-grid" id="vacancy-grid">${rows.map(v=>{const occupied=Number(v.ocupada)===1||v.ocupada===true;const num=v.numero??v.vaga_numero??v.id;return `<article class="vacancy ${occupied?"occupied":"free"}" data-state="${occupied?"ocupada":"livre"}" data-search="${esc(`${num} ${v.tipo_veiculo||""} ${v.plano||""}`.toLocaleLowerCase("pt-BR"))}"><span class="vacancy-icon">▰</span><strong>${esc(num)}</strong><small>${esc(v.tipo_veiculo)}</small><small>${esc(v.plano)}</small>${badge(occupied?"Ocupada":"Livre")}</article>`}).join("")||'<div class="empty-row">Nenhuma vaga cadastrada.</div>'}</div>`)}`;
    const filter=()=>{$$(".vacancy").forEach(el=>el.hidden=!(el.dataset.search.includes($("#search-table").value.toLocaleLowerCase("pt-BR"))&&(!$("#vacancy-filter").value||el.dataset.state===$("#vacancy-filter").value)));};
    $("#search-table").addEventListener("input",filter);$("#vacancy-filter").addEventListener("change",filter);
    $("#new-vacancy").onclick=()=>{modal("Cadastrar vaga",`<form id="vacancy-form" class="form-grid">${field("Número da vaga","numero","number",true,"Ex.: 1",'min="1" max="9999"')}${select("Tipo de veículo","tipo_veiculo_id",tipos)}${select("Plano","plano_id",planos.filter(p=>Number(p.ativo)===1))}<div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar vaga</button></div></form>`);
    catchForm($("#vacancy-form"),async e=>{const d=fd(e.currentTarget);["numero","tipo_veiculo_id","plano_id"].forEach(k=>d[k]=Number(d[k]));await api("/api/vagas",{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Vaga cadastrada.");await vacancies();});};
  }
  async function contracts(){
    const [rows,clientes,veiculos]=await Promise.all([api("/api/contratos"),api("/api/clientes"),api("/api/veiculos")]);
    $("#app-content").innerHTML=panel("Contratos mensalistas","Um contrato por veículo; valor mensal registrado no momento da contratação.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar cliente ou placa..."></label><button class="btn btn-primary" id="new-contract">＋ Novo contrato</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"id",label:"Nº"},{key:"cliente_nome",label:"Cliente"},{key:"placa",label:"Placa"},{key:"valor_mensal",label:"Mensalidade",render:money},{key:"dia_vencimento",label:"Vencimento",render:v=>`Dia ${esc(v)}`},{key:"data_inicio",label:"Início",render:date},{key:"data_fim",label:"Fim",render:date},{key:"situacao",label:"Status",render:(v,r)=>badge(r.data_fim?"Encerrado":"Vigente")},{key:"acao",label:"Ação",render:(v,r)=>!r.data_fim?`<button class="btn btn-secondary btn-sm" data-end="${esc(r.id??r.contrato_id)}">Encerrar</button>`:"—"}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $("#new-contract").onclick=()=>{modal("Novo contrato mensalista",`<form id="contract-form" class="form-grid">${select("Cliente","cliente_id",clientes.map(c=>({value:c.id??c.cliente_id,label:c.nome})))}${select("Veículo","veiculo_id",veiculos.map(v=>({value:v.id??v.veiculo_id,label:`${v.placa} · ${v.cliente_nome||""}`})))}${moneyField("Valor mensal (R$)","valor_mensal",true)}${field("Dia de vencimento","dia_vencimento","number",true,"1 a 28",'min="1" max="28"')}${field("Data de início","data_inicio","date")}<div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Criar contrato</button></div></form>`);
    catchForm($("#contract-form"),async e=>{const d=fd(e.currentTarget);["cliente_id","veiculo_id","dia_vencimento"].forEach(k=>d[k]=Number(d[k]));await api("/api/contratos",{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Contrato criado.");await contracts();});};
    $$("[data-end]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.end;modal("Encerrar contrato",`<form id="end-contract-form" class="form-stack"><label>Data de encerramento<input name="data_fim" type="date" required value="${new Date().toLocaleDateString("en-CA")}"></label><label>Motivo<select name="motivo"><option value="cancelado_cliente">Cancelado pelo cliente</option><option value="inadimplencia">Inadimplência</option><option value="troca_veiculo">Troca de veículo</option><option value="outro">Outro</option></select></label><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-danger">Encerrar contrato</button></div></form>`);catchForm($("#end-contract-form"),async e=>{await api(`/api/contratos/${id}/encerrar`,{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Contrato encerrado.");await contracts();});}));
  }
  async function payments(){
    const rows=await api("/api/pagamentos"),pending=rows.filter(r=>r.situacao==="aberto");
    $("#app-content").innerHTML=`<div class="stats-grid">${stat("Cobranças listadas",rows.length,"◉","Registros recentes")}${stat("Em aberto",pending.length,"◷","Aguardando recebimento")}${stat("Total em aberto",money(pending.reduce((s,r)=>s+Number(r.valor||0),0)),"＄","Somatório pendente")}${stat("Pagas",rows.filter(r=>r.situacao==="pago").length,"✓","Recebimentos confirmados")}</div>${panel("Pagamentos e mensalidades","Recebimentos exigem caixa aberto.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar cliente, placa ou situação..."></label><button class="btn btn-secondary" id="generate-bills">Gerar mensalidades do mês</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"id",label:"Nº"},{key:"cliente_nome",label:"Cliente",render:v=>v||"Horista"},{key:"placa",label:"Placa"},{key:"competencia",label:"Competência",render:date},{key:"vencimento",label:"Vencimento",render:date},{key:"valor",label:"Valor",render:money},{key:"situacao",label:"Situação",render:badge},{key:"forma_pagamento",label:"Forma"},{key:"acao",label:"Ação",render:(v,r)=>r.situacao==="aberto"&&r.contrato_id?`<button class="btn btn-primary btn-sm" data-receive="${esc(r.id??r.pagamento_id)}">Receber</button>`:"—"}],rows)}</div>`)}`;
    wireSearch($("#search-table"),$("#table-results"));
    $("#generate-bills").onclick=async()=>{try{const r=await api("/api/pagamentos/gerar-mensalidades",{method:"POST",body:JSON.stringify({})});toast(`${r.criadas??0} mensalidade(s) gerada(s).`);await payments();}catch(e){toast(e.message,"error");}};
    $$("[data-receive]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.receive;modal("Receber mensalidade",`<form id="receive-form" class="form-stack"><label>Forma de pagamento<select name="forma_pagamento" required><option value="dinheiro">Dinheiro</option><option value="pix">Pix</option><option value="cartao_debito">Cartão de débito</option><option value="cartao_credito">Cartão de crédito</option></select></label><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Confirmar recebimento</button></div></form>`);catchForm($("#receive-form"),async e=>{await api(`/api/pagamentos/${id}/receber`,{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Pagamento recebido.");await payments();});}));
  }
  async function catalogs(){
    const keys=[["tipos_veiculo","Tipos de veículo"],["marcas","Marcas"],["modelos","Modelos"],["cores","Cores"],["planos","Planos"]];
    const [data,precos]=await Promise.all([Promise.all(keys.map(async([key,label])=>({key,label,rows:await api(`/api/catalogos/${key}`)}))),api("/api/precos")]);
    const tiposCat=data[0].rows,planosCat=data[4].rows.filter(p=>Number(p.ativo)===1);const marcasCat=data[1].rows;const marcaNome=id=>marcasCat.find(m=>String(m.id)===String(id))?.nome||"—";const isAdmin=user?.nivel_acesso==="administrador";
    const precoPanel=panel("Preços","Valor cobrado por plano e tipo de veículo. A saída do horista depende do preço cadastrado.",`<div class="toolbar"><span></span><button class="btn btn-primary" id="new-price">＋ Novo preço</button></div><div style="height:15px"></div>${table([{key:"plano",label:"Plano"},{key:"tipo_veiculo",label:"Tipo de veículo"},{key:"valor",label:"Valor",render:money},{key:"valor_diaria",label:"Diária",render:v=>v==null?"—":money(v)},{key:"acao",label:"Ação",render:(v,r)=>`<button class="btn btn-secondary btn-sm" data-edit-price="${esc(r.id)}">Editar</button>`}],precos,"Nenhum preço cadastrado.")}`);
    $("#app-content").innerHTML=`<div class="notice notice-info">Planos, tipos, marcas, modelos e cores estão disponíveis para consulta. Os preços podem ser cadastrados e editados abaixo.</div>${precoPanel}<div style="height:15px"></div><div class="catalog-grid">${data.map(x=>`<section class="panel"><div class="panel-heading"><div><h2>${esc(x.label)}</h2><p>${x.rows.length} registro(s)</p></div>${x.key==="planos"||(x.key==="tipos_veiculo"&&!isAdmin)?"":`<button class="btn btn-primary btn-sm" data-new-cat="${x.key}">＋ Novo</button>`}</div>${table([{key:"id",label:"Código"},{key:"nome",label:"Nome"},...(x.key==="modelos"&&x.rows.some(r=>r.tipo_veiculo_id!=null)?[{key:"tipo_veiculo_id",label:"Tipo de veículo",render:v=>esc(tiposCat.find(t=>String(t.id)===String(v))?.nome||"—")}]:[]),...(x.key==="modelos"&&x.rows.some(r=>r.marca_id!=null)?[{key:"marca_id",label:"Marca",render:v=>esc(marcaNome(v))}]:[]),{key:"ativo",label:"Status",render:v=>v===undefined?"—":badge(v)}],x.rows)}</section>`).join("")}</div>`;
    $("#new-price").onclick=()=>{modal("Cadastrar preço",`<form id="price-form" class="form-grid">${select("Plano","plano_id",planosCat)}${select("Tipo de veículo","tipo_veiculo_id",tiposCat)}${moneyField("Valor (R$)","valor",true)}${moneyField("Diária (R$), opcional","valor_diaria",false)}<div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar preço</button></div></form>`);
    catchForm($("#price-form"),async e=>{const d=fd(e.currentTarget);["plano_id","tipo_veiculo_id"].forEach(k=>d[k]=Number(d[k]));if(d.valor_diaria==="")delete d.valor_diaria;await api("/api/precos",{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Preço cadastrado.");await catalogs();});};
    $$("[data-edit-price]").forEach(b=>b.addEventListener("click",()=>{const r=precos.find(x=>String(x.id)===b.dataset.editPrice);modal(`Editar preço · ${r.plano} · ${r.tipo_veiculo}`,`<form id="price-edit-form" class="form-grid">${moneyField("Valor (R$)","valor",true,r.valor)}${moneyField("Diária (R$), opcional","valor_diaria",false,r.valor_diaria??"")}<div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar alterações</button></div></form>`);
    catchForm($("#price-edit-form"),async e=>{const d=fd(e.currentTarget);if(d.valor_diaria==="")delete d.valor_diaria;await api(`/api/precos/${r.id}`,{method:"PUT",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Preço atualizado.");await catalogs();});}));
    const nomesCat={tipos_veiculo:"tipo de veículo",marcas:"marca",modelos:"modelo",cores:"cor"};
    $$("[data-new-cat]").forEach(b=>b.addEventListener("click",()=>{const key=b.dataset.newCat;const usaMarca=key==="modelos"&&data[2].rows.some(r=>r.marca_id!=null);
      modal(`Cadastrar ${nomesCat[key]}`,`<form id="cat-form" class="form-stack">${key==="modelos"?select("Tipo de veículo","tipo_veiculo_id",tiposCat):""}${key==="modelos"&&(usaMarca||!data[2].rows.length)?select("Marca","marca_id",marcasCat):""}${field("Nome","nome","text",true,"",'maxlength="60"')}<div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar</button></div></form>`);
      catchForm($("#cat-form"),async e=>{const d=fd(e.currentTarget);if(d.tipo_veiculo_id)d.tipo_veiculo_id=Number(d.tipo_veiculo_id);else delete d.tipo_veiculo_id;if(d.marca_id)d.marca_id=Number(d.marca_id);else delete d.marca_id;await api(`/api/catalogos/${key}`,{method:"POST",body:JSON.stringify(d)});$("#modal-root").innerHTML="";toast("Cadastrado com sucesso.");await catalogs();});}));
  }
  async function settings(){
    const c=await api("/api/configuracoes");
    $("#app-content").innerHTML=panel("Configurações do estacionamento","Altere regras que passam a valer para novas saídas.",`<form id="settings-form" class="form-grid content-narrow">${field("Nome do estacionamento","nome_estacionamento","text",true,"Nome do estacionamento",'maxlength="80" value="'+esc(c.nome_estacionamento||"")+'"')}${field("Tolerância (minutos)","tolerancia_minutos","number",true,"10",'min="0" max="1440" value="'+esc(c.tolerancia_minutos??10)+'"')}${field("Fração de cobrança (minutos)","fracao_minutos","number",true,"30",'min="1" max="60" value="'+esc(c.fracao_minutos??30)+'"')}${moneyField("Preço por hora (R$)","valor_hora",false,c.valor_hora??"")}${moneyField("Diária (R$), opcional","valor_diaria",false,c.valor_diaria??"")}<label class="span-2">Regra de arredondamento<select name="arredondamento"><option value="fracao" ${c.arredondamento==="fracao"?"selected":""}>Por fração de tempo</option><option value="hora_cheia" ${c.arredondamento==="hora_cheia"?"selected":""}>Hora cheia</option></select></label><div class="form-actions span-2"><button class="btn btn-primary">Salvar configurações</button></div></form>`);
    catchForm($("#settings-form"),async e=>{const d=fd(e.currentTarget);["tolerancia_minutos","fracao_minutos"].forEach(k=>d[k]=Number(d[k]));for(const k of ["valor_hora","valor_diaria"])if(d[k]==="")delete d[k];await api("/api/configuracoes",{method:"PUT",body:JSON.stringify(d)});toast("Configurações atualizadas.");});
  }
  async function users(){
    const rows=await api("/api/usuarios");
    $("#app-content").innerHTML=panel("Usuários do sistema","Apenas administradores podem gerenciar contas.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar nome, login ou e-mail..."></label><button class="btn btn-primary" id="new-user">＋ Novo usuário</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"nome",label:"Nome"},{key:"login",label:"Login"},{key:"email",label:"E-mail"},{key:"nivel_acesso",label:"Perfil",render:badge},{key:"ativo",label:"Ativo",render:badge},{key:"acao",label:"Ação",render:(v,r)=>Number(r.ativo)===1?`<button class="btn btn-danger btn-sm" data-disable="${esc(r.id??r.usuario_id)}">Desativar</button>`:"Desativado"}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $("#new-user").onclick=()=>{modal("Criar usuário",`<form id="user-form" class="form-grid">${field("Nome completo","nome")}${field("E-mail","email","email")}${field("Login","login")}${field("Senha provisória","senha_provisoria","password",true,"Mínimo de 8 caracteres",'minlength="8"')}<label class="span-2">Nível de acesso<select name="nivel_acesso"><option value="operador">Operador</option><option value="administrador">Administrador</option></select></label><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Criar usuário</button></div></form>`);
    catchForm($("#user-form"),async e=>{await api("/api/usuarios",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Usuário criado. A troca de senha será exigida no próximo login.");await users();});};
    $$("[data-disable]").forEach(b=>b.addEventListener("click",async()=>{if(!confirm("Deseja desativar este usuário?"))return;try{await api(`/api/usuarios/${b.dataset.disable}/desativar`,{method:"POST",body:JSON.stringify({})});toast("Usuário desativado.");await users();}catch(e){toast(e.message,"error");}}));
  }
  async function audit(){
    const rows=await api("/api/auditoria");
    $("#app-content").innerHTML=panel("Registro de auditoria","Alterações administrativas registradas pelo sistema.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar tabela, ação ou usuário..."></label></div><div style="height:15px"></div><div id="table-results">${table([{key:"data_hora",label:"Data e hora",render:dt},{key:"usuario_nome",label:"Usuário"},{key:"tabela",label:"Tabela"},{key:"registro_id",label:"Registro"},{key:"acao",label:"Ação",render:badge},{key:"dados_antes",label:"Antes",render:v=>v?`<button class="btn btn-secondary btn-sm" data-json="${esc(v)}">Ver</button>`:"—"},{key:"dados_depois",label:"Depois",render:v=>v?`<button class="btn btn-secondary btn-sm" data-json="${esc(v)}">Ver</button>`:"—"}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $$("[data-json]").forEach(b=>b.addEventListener("click",()=>{let val=b.dataset.json;try{val=JSON.stringify(JSON.parse(val),null,2)}catch{}modal("Detalhes do registro",`<pre class="json-view">${esc(val)}</pre>`);}));
  }
  async function login(){
    $("#login-form")?.addEventListener("submit",async e=>{e.preventDefault();const err=$("#login-error");err.textContent="";const b=e.currentTarget.querySelector('[type="submit"]');b.disabled=true;try{const r=await api("/api/login",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});go(r.proxima||"/");}catch(ex){err.textContent=ex.message;}finally{b.disabled=false;}});
    const pass=$("#login-password");pass?.addEventListener("keyup",e=>{$("#caps-warning").hidden=!e.getModifierState("CapsLock");});
  }
  async function changePassword(){
    const pass=$("#new-password");pass?.addEventListener("input",()=>{const v=pass.value;const tests={length:v.length>=8,letters:/[A-Za-zÀ-ÿ]/.test(v),number:/\d/.test(v)};Object.entries(tests).forEach(([k,ok])=>{const el=$(`[data-rule="${k}"]`);if(el){el.classList.toggle("valid",ok);el.textContent=(ok?"✓ ":"○ ")+({length:"Pelo menos 8 caracteres",letters:"Contém letras",number:"Contém números"}[k]);}});});
    catchForm($("#change-password-form"),async e=>{const d=fd(e.currentTarget);if(d.nova_senha!==d.confirmacao)throw new Error("A confirmação da senha não corresponde.");delete d.confirmacao;const r=await api("/api/trocar-senha",{method:"POST",body:JSON.stringify(d)});toast(r.mensagem||"Senha alterada.");go("/");});
  }
  function applyAppearance(prefs={}){
    document.body.classList.toggle("light-theme",prefs.tema==="claro");
    document.body.classList.toggle("text-large",prefs.tamanho_texto==="grande");
    ["azul","verde","violeta","dourado"].forEach(c=>document.body.classList.toggle("accent-"+c,(prefs.cor_destaque||"azul")===c));
    user=user||{};
    user.preferencias={tema:"escuro",tamanho_texto:"normal",cor_destaque:"azul",sons:"ligados",...prefs};
  }
  function appearance(){
    const form=$("#appearance-form");
    if(!form)return;
    catchForm(form,async e=>{
      const d=fd(e.currentTarget);
      const saved=await api("/api/sessao/preferencias",{method:"PUT",body:JSON.stringify(d)});
      applyAppearance(saved.preferencias||d);
      $("#modal-root").innerHTML="";
      toast("Preferências aplicadas.");
    });
  }
  async function boot(){
    await initCsrf();
    if(page==="login"){login();return;}
    setupShell();await loadUser();appearance();await updateCashIndicator();
    if(page==="trocar_senha"){changePassword();return;}
    const renderers={painel:dashboard,movimentacoes:movements,caixa:cash,clientes:clients,veiculos:vehicles,vagas:vacancies,contratos:contracts,pagamentos:payments,catalogos:catalogs,configuracoes:settings,usuarios:users,auditoria:audit};
    if(renderers[page])try{await renderers[page]();}catch(e){$("#app-content").innerHTML=`<div class="notice notice-error"><strong>Não foi possível carregar esta tela.</strong><br>${esc(e.message)}<br><small>Confira se a rota da API correspondente existe no backend.</small></div><button class="btn btn-secondary" onclick="location.reload()">Tentar novamente</button>`;}
  }
  document.addEventListener("DOMContentLoaded",boot);
})();

function modal(title, body) {
  const root = document.querySelector("#modal-root");

  if (!root) {
    console.error('Elemento "#modal-root" não encontrado.');
    return;
  }

  // Remove o listener do modal anterior, se existir.
  if (root._modalEscapeHandler) {
    document.removeEventListener(
      "keydown",
      root._modalEscapeHandler
    );

    root._modalEscapeHandler = null;
  }

  // Cria a janela do modal.
  root.innerHTML = `
    <div class="modal-backdrop" data-backdrop>
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-label="${esc(title)}"
      >
        <div class="modal-header">
          <h2>${esc(title)}</h2>

          <button
            type="button"
            class="modal-close"
            data-close
            aria-label="Fechar janela"
          >
            ×
          </button>
        </div>

        <div class="modal-body">
          ${body}
        </div>
      </section>
    </div>
  `;

  // Ativa a validação dos formulários.
  root.querySelectorAll("form").forEach(form => {
    enableLiveValidation(form);
  });

  const backdrop = root.querySelector("[data-backdrop]");
  const modalWindow = root.querySelector(".modal");

  // Função central para fechar o modal.
  function fecharModal() {
    root.innerHTML = "";

    if (root._modalEscapeHandler) {
      document.removeEventListener(
        "keydown",
        root._modalEscapeHandler
      );

      root._modalEscapeHandler = null;
    }
  }

  // Fecha ao clicar no X ou em qualquer botão com data-close.
  root.querySelectorAll("[data-close]").forEach(botao => {
    botao.addEventListener("click", event => {
      event.preventDefault();
      fecharModal();
    });
  });

  // Fecha ao clicar fora da janela.
  backdrop.addEventListener("click", event => {
    if (event.target === backdrop) {
      fecharModal();
    }
  });

  // Impede que cliques dentro do modal fechem a janela.
  modalWindow.addEventListener("click", event => {
    event.stopPropagation();
  });

  // Fecha ao pressionar Esc.
  root._modalEscapeHandler = event => {
    if (
      event.key === "Escape" &&
      root.querySelector(".modal")
    ) {
      fecharModal();
    }
  };

  document.addEventListener(
    "keydown",
    root._modalEscapeHandler
  );
}