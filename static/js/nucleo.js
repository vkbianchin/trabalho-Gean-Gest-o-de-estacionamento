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
  async function api(url,opts={},tentarNovamente=true){
    const options={credentials:"same-origin",...opts};
    options.headers={Accept:"application/json",...(options.body?{"Content-Type":"application/json"}:{}),...(csrfToken?{"X-CSRFToken":csrfToken}:{}),...(options.headers||{})};
    let res;try{res=await fetch(url,options);}catch{throw new Error("Não foi possível conectar ao servidor Flask.");}
    const ct=res.headers.get("content-type")||"";let data=ct.includes("application/json")?await res.json():await res.text();
    if(res.status===400&&data&&data.codigo==="csrf"&&tentarNovamente){await initCsrf();return api(url,opts,false);}
    if(!res.ok){if(res.status===401&&page!=="login")location.replace("/login");throw new Error((data&&(data.mensagem||data.erro||data.message))||"Não foi possível concluir a operação.");}
    return data;
  }
  async function initCsrf(){try{const r=await fetch("/api/csrf",{credentials:"same-origin"});if(r.ok){const d=await r.json();csrfToken=d.csrf_token||"";const m=$('meta[name="csrf-token"]');if(m)m.content=csrfToken;}}catch{}}
  const fd = form => Object.fromEntries(new FormData(form).entries());
  const moneyField = (label,name,required=true,value="") => `<label>${label}<input name="${name}" type="number" min="0" step=".01" ${required?"required":""} value="${esc(value)}"></label>`;
  const field = (label,name,type="text",required=true,placeholder="",extra="") => `<label>${label}<input name="${name}" type="${type}" ${required?"required":""} placeholder="${placeholder}" ${extra}></label>`;
  const select = (label,name,options,required=true) => `<label>${label}<select name="${name}" ${required?"required":""}><option value="">Selecione...</option>${(options||[]).map(o=>`<option value="${esc(o.value??o.id)}">${esc(o.label??o.nome)}</option>`).join("")}</select></label>`;
  function badge(value){if(value===1||value===true)value="Ativo";else if(value===0||value===false)value="Inativo";const s=String(value??"").toLowerCase();let cls="badge-blue";if(["ativo","pago","aberto","vigente","disponível","disponivel","livre","sim"].includes(s))cls="badge-green";else if(["inativo","cancelado","fechado","encerrado","ocupada","ocupado","não","nao"].includes(s))cls="badge-gray";else if(s.includes("atras")||s.includes("inadimpl")||s.includes("vencid"))cls="badge-red";else if(s.includes("pend")||s.includes("abert"))cls="badge-amber";return `<span class="badge ${cls}">${esc(value)}</span>`;}
  function table(cols,rows,empty="Nenhum registro encontrado."){if(!rows?.length)return `<div class="empty-row">${esc(empty)}</div>`;return `<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th>${esc(c.label)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${c.render?c.render(r[c.key],r):esc(r[c.key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;}
  function stat(label,value,icon,note){return `<article class="stat-card"><div class="stat-top"><span>${esc(label)}</span><span class="stat-icon">${icon}</span></div><div class="stat-number">${esc(value)}</div><div class="stat-note">${esc(note)}</div></article>`;}
  function panel(title,subtitle,body,right=""){return `<section class="panel"><div class="panel-heading"><div><h2>${title}</h2>${subtitle?`<p>${subtitle}</p>`:""}</div>${right}</div>${body}</section>`;}
  function cpfValido(valor){const cpf=String(valor||"").replace(/\D/g,"");if(cpf.length!==11||/^(\d)\1{10}$/.test(cpf))return false;let soma=0;for(let i=0;i<9;i++)soma+=Number(cpf[i])*(10-i);let dig=(soma*10)%11;if(dig===10)dig=0;if(dig!==Number(cpf[9]))return false;soma=0;for(let i=0;i<10;i++)soma+=Number(cpf[i])*(11-i);dig=(soma*10)%11;if(dig===10)dig=0;return dig===Number(cpf[10]);}
  function cnpjValido(valor){const n=String(valor||"").replace(/\D/g,"");if(n.length!==14||/^(\d)\1{13}$/.test(n))return false;const calc=tam=>{const pesos=tam===12?[5,4,3,2,9,8,7,6,5,4,3,2]:[6,5,4,3,2,9,8,7,6,5,4,3,2];let soma=0;for(let i=0;i<pesos.length;i++)soma+=Number(n[i])*pesos[i];const r=soma%11;return r<2?0:11-r;};return calc(12)===Number(n[12])&&calc(13)===Number(n[13]);}
  function maskDocumento(valor,juridica){const n=String(valor||"").replace(/\D/g,"").slice(0,juridica?14:11);if(juridica)return n.replace(/^(\d{2})(\d)/,"$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/,"$1.$2.$3").replace(/\.(\d{3})(\d)/,".$1/$2").replace(/(\d{4})(\d)/,"$1-$2");return n.replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d)/,"$1.$2").replace(/(\d{3})(\d{1,2})$/,"$1-$2");}
  const fmtDoc=v=>{const n=String(v||"").replace(/\D/g,"");return n?maskDocumento(n,n.length>11):"—";};
  const fmtDuracao=m=>{m=Math.max(0,Math.floor(m));const d=Math.floor(m/1440),h=Math.floor((m%1440)/60),mi=m%60,p=[];if(d)p.push(d+(d>1?" dias":" dia"));if(h)p.push(h+"h");if(mi||!p.length)p.push((h||d)?String(mi).padStart(2,"0")+"min":mi+"min");return p.join(" ");};
  const permanencia=(a,b)=>a&&b?fmtDuracao((new Date(b)-new Date(a))/60000):"—";
  function validationMessage(el){const v=el.value.trim(),name=(el.name||"").toLowerCase(),label=el.closest("label")?.childNodes?.[0]?.textContent?.trim()||el.getAttribute("aria-label")||name||"Este campo";if(!v){return el.required?`${label}: este campo é obrigatório.`:"";}if(v.includes("@")&&el.type!=="email"&&el.type!=="password"&&name!=="email"&&el.form?.id!=="login-form")return "Use @ somente no campo de e-mail.";if(name==="documento"||name==="cpf"){const juridica=el.form?.elements?.tipo_pessoa?.value==="juridica",digits=v.replace(/\D/g,"");if(juridica){if(digits.length<14)return "Digite os 14 números do CNPJ.";if(!cnpjValido(v))return "CNPJ inválido. Confira os números digitados.";}else{if(digits.length<11)return "Digite os 11 números do CPF.";if(!cpfValido(v))return "CPF inválido. Confira os números digitados.";}}if(name==="cnpj"){const digits=v.replace(/\D/g,"");if(digits.length<14)return "Digite os 14 números do CNPJ.";if(!cnpjValido(v))return "CNPJ inválido. Confira os números digitados.";}if(name==="cep"&&v.replace(/\D/g,"").length!==8)return "CEP deve conter 8 números.";if(name==="telefone"){const n=v.replace(/\D/g,"");if(n.length<10||n.length>11)return "Telefone deve ter DDD e 10 ou 11 números.";}if(el.type==="email"&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))return "Digite um e-mail válido.";if(name==="placa"&&!/^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(v.replace(/[^A-Z0-9]/g,"").toUpperCase()))return "Placa inválida. Use ABC1234 ou ABC1D23.";if(el.type==="number"){const n=Number(v),min=el.min!==""?Number(el.min):null,max=el.max!==""?Number(el.max):null;if(!Number.isFinite(n))return "Digite um número válido.";if(min!==null&&n<min)return `O valor mínimo é ${min}.`;if(max!==null&&n>max)return `O valor máximo é ${max}.`;}if(el.minLength>0&&v.length<el.minLength)return `Digite pelo menos ${el.minLength} caracteres.`;if(el.maxLength>0&&v.length>el.maxLength)return `Digite no máximo ${el.maxLength} caracteres.`;return "";}
  function validateField(el,show=true){if(!el||el.disabled||["submit","button","reset","hidden"].includes(el.type))return true;const msg=validationMessage(el);el.setAttribute("aria-invalid",msg?"true":"false");let hint=el.parentElement?.querySelector(`.live-field-error[data-for="${CSS.escape(el.name||el.id||"")}"]`);if(!hint&&el.parentElement){hint=document.createElement("small");hint.className="live-field-error";hint.dataset.for=el.name||el.id||"";hint.setAttribute("aria-live","polite");el.insertAdjacentElement("afterend",hint);}if(hint){hint.textContent=show?msg:"";hint.hidden=!show||!msg;}return !msg;}
  function enableLiveValidation(form){if(!form||form.dataset.liveValidation==="true")return;form.dataset.liveValidation="true";const touched=new WeakSet();form.querySelectorAll("input,select,textarea").forEach(el=>{el.addEventListener("input",()=>{touched.add(el);if(el.name==="documento_recibo"){const n=el.value.replace(/\D/g,"");el.value=maskDocumento(n,n.length>11);}else if(el.name==="cnpj"){el.value=maskDocumento(el.value,true);}else if(el.name==="documento"||el.name==="cpf"){el.value=maskDocumento(el.value,el.form?.elements?.tipo_pessoa?.value==="juridica");}else if(el.name==="cep"){let n=el.value.replace(/\D/g,"").slice(0,8);el.value=n.length>5?n.slice(0,5)+"-"+n.slice(5):n;}else if(el.name==="telefone"){let n=el.value.replace(/\D/g,"").slice(0,11);if(n.length>10)el.value=n.replace(/(\d{2})(\d{5})(\d{4})/,"($1) $2-$3");else if(n.length>6)el.value=n.replace(/(\d{2})(\d{4})(\d{0,4})/,"($1) $2-$3");else if(n.length>2)el.value=n.replace(/(\d{2})(\d+)/,"($1) $2");else el.value=n;}else if(el.name==="placa")el.value=el.value.toUpperCase().replace(/[^A-Z0-9]/g,"").slice(0,7);validateField(el,true);});el.addEventListener("blur",()=>{touched.add(el);validateField(el,true);});});form.addEventListener("submit",e=>{let first=null;form.querySelectorAll("input,select,textarea").forEach(el=>{if(!validateField(el,true)&&!first)first=el;});if(first){e.preventDefault();e.stopImmediatePropagation();first.focus();}} ,true);}
  function modal(title,body){const root=$("#modal-root");root.innerHTML=`<div class="modal-backdrop" data-backdrop><section class="modal" role="dialog" aria-modal="true"><div class="modal-header"><h2>${esc(title)}</h2><button type="button" class="modal-close" data-close>×</button></div><div class="modal-body">${body}</div></section></div>`;root.querySelectorAll("form").forEach(enableLiveValidation);root.querySelector("[data-backdrop]").addEventListener("click",e=>{if(e.target.matches("[data-backdrop]")||e.target.closest("[data-close]"))root.innerHTML="";});// O clique dentro da janela só fecha quando vem de um botão [data-close]; clicar no fundo também fecha.
    const aoTeclar=ev=>{if(!root.querySelector(".modal")){document.removeEventListener("keydown",aoTeclar);return;}if(ev.key==="Escape"){root.innerHTML="";document.removeEventListener("keydown",aoTeclar);}};
    document.addEventListener("keydown",aoTeclar);}
  function catchForm(form,fn){if(!form)return;enableLiveValidation(form);form.addEventListener("submit",async e=>{e.preventDefault();const b=form.querySelector('[type="submit"]');if(b)b.disabled=true;try{await fn(e); }catch(err){toast(err.message||"Erro inesperado.","error");}finally{if(b)b.disabled=false;}});}
  function wireSearch(input,root){input?.addEventListener("input",()=>{const q=input.value.toLocaleLowerCase("pt-BR");root?.querySelectorAll("tbody tr").forEach(tr=>tr.hidden=!tr.textContent.toLocaleLowerCase("pt-BR").includes(q));root?.querySelectorAll(".vacancy").forEach(el=>el.hidden=!el.dataset.search.includes(q));});}
  /* Caixa de confirmação (substitui o confirm() do navegador). Resolve true/false. */
  function confirmar(titulo,mensagem,rotulo="Confirmar",perigo=false){
    return new Promise(resolve=>{
      modal(titulo,`<p>${esc(mensagem)}</p><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button type="button" class="btn ${perigo?"btn-danger":"btn-primary"}" id="confirm-yes">${esc(rotulo)}</button></div>`);
      const raiz=$("#modal-root");
      $("#confirm-yes").addEventListener("click",()=>{raiz.innerHTML="";resolve(true);});
      raiz.querySelectorAll("[data-close]").forEach(el=>el.addEventListener("click",()=>resolve(false)));
      raiz.querySelector("[data-backdrop]")?.addEventListener("click",ev=>{if(ev.target===ev.currentTarget)resolve(false);});
    });
  }
  /* Pede o motivo (mínimo de 5 caracteres) antes de cancelar ou estornar. Resolve o texto ou null. */
  function pedirMotivo(titulo,mensagem,rotulo="Confirmar"){
    return new Promise(resolve=>{
      modal(titulo,`<form id="motivo-form" class="form-stack"><p>${esc(mensagem)}</p><label>Motivo<textarea name="motivo" rows="3" maxlength="200" required placeholder="Descreva o motivo (mínimo de 5 caracteres)"></textarea></label><div class="form-actions"><button type="button" class="btn btn-secondary" data-close>Voltar</button><button class="btn btn-danger">${esc(rotulo)}</button></div></form>`);
      const raiz=$("#modal-root");
      $("#motivo-form").addEventListener("submit",ev=>{
        ev.preventDefault();const motivo=ev.currentTarget.motivo.value.trim();
        if(motivo.length<5){toast("Descreva o motivo com pelo menos 5 caracteres.","error");return;}
        raiz.innerHTML="";resolve(motivo);
      });
      raiz.querySelectorAll("[data-close]").forEach(el=>el.addEventListener("click",()=>resolve(null)));
      raiz.querySelector("[data-backdrop]")?.addEventListener("click",ev=>{if(ev.target===ev.currentTarget)resolve(null);});
    });
  }
  const ehAdmin=()=>user?.nivel_acesso==="administrador";
  function go(url){location.href=url;}
  function trocarPagina(url){location.replace(url);}
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
    $("#logout-button")?.addEventListener("click",async()=>{try{await api("/api/logout",{method:"POST",body:JSON.stringify({})});trocarPagina("/login");}catch(e){toast(e.message,"error");}});
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
  async function verificarSessao(){
    // Chamada quando o navegador restaura a página do histórico (botão "voltar"): confere se ainda há sessão.
    try{const r=await fetch("/api/sessao",{credentials:"same-origin",cache:"no-store"});if(page==="login"){if(r.ok)location.replace("/");}else if(r.status===401)location.replace("/login");}catch{}
  }
  window.ParkFlow = { $, $$, page, esc, money, dt, date, toast, api, fd, moneyField, field, select, badge, table, stat, panel, cpfValido, cnpjValido, maskDocumento, fmtDoc, fmtDuracao, permanencia, modal, catchForm, wireSearch, go, trocarPagina, updateCashIndicator, applyAppearance, appearance, confirmar, pedirMotivo, ehAdmin, usuario: () => user, telas: {} };
  async function boot(){
    await initCsrf();
    window.addEventListener("pageshow",e=>{if(e.persisted)verificarSessao();});
    const telas=window.ParkFlow.telas;   // cada arquivo em js/telas/ registra a sua tela aqui
    if(page==="login"){telas.login?.();return;}
    setupShell();await loadUser();appearance();await updateCashIndicator();
    if(page==="trocar_senha"){telas.trocar_senha?.();return;}
    if(telas[page])try{await telas[page]();}catch(e){
      $("#app-content").innerHTML=`<div class="notice notice-error"><strong>Não foi possível carregar esta tela.</strong><br>${esc(e.message)}<br><small>Confira se a rota da API correspondente existe no backend.</small></div><button class="btn btn-secondary" id="retry-load">Tentar novamente</button>`;
      $("#retry-load")?.addEventListener("click",()=>location.reload());
    }
  }
  document.addEventListener("DOMContentLoaded",boot);
})();
