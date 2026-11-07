/* Tela: usuarios */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { esc, toast, api, fd, field, select, badge, table, panel, modal, catchForm, wireSearch, confirmar } = P;
  const $ = P.$;
  const $$ = P.$$;

  async function users(){
    const rows=await api("/api/usuarios");
    $("#app-content").innerHTML=panel("Usuários do sistema","Apenas administradores podem gerenciar contas.",`<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar nome, login ou e-mail..."></label><button class="btn btn-primary" id="new-user">＋ Novo usuário</button></div><div style="height:15px"></div><div id="table-results">${table([{key:"nome",label:"Nome"},{key:"login",label:"Login"},{key:"email",label:"E-mail"},{key:"nivel_acesso",label:"Perfil",render:badge},{key:"ativo",label:"Ativo",render:badge},{key:"acao",label:"Ação",render:(v,r)=>{const id=esc(r.id??r.usuario_id),eu=Number(P.usuario()?.usuario_id)===Number(r.id);return Number(r.ativo)===1?(eu?"Você":`<button class="btn btn-secondary btn-sm" data-reset="${id}">Redefinir senha</button> <button class="btn btn-danger btn-sm" data-disable="${id}">Desativar</button>`):`<button class="btn btn-secondary btn-sm" data-activate="${id}">Reativar</button>`;}}],rows)}</div>`);
    wireSearch($("#search-table"),$("#table-results"));
    $("#new-user").onclick=()=>{modal("Criar usuário",`<form id="user-form" class="form-grid">${field("Nome completo","nome")}${field("E-mail","email","email")}${field("Login","login")}${field("Senha provisória","senha_provisoria","password",true,"Mínimo de 8 caracteres",'minlength="8"')}<label class="span-2">Nível de acesso<select name="nivel_acesso"><option value="operador">Operador</option><option value="administrador">Administrador</option></select></label><div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Criar usuário</button></div></form>`);
    catchForm($("#user-form"),async e=>{await api("/api/usuarios",{method:"POST",body:JSON.stringify(fd(e.currentTarget))});$("#modal-root").innerHTML="";toast("Usuário criado. A troca de senha será exigida no próximo login.");await users();});};
    $$("[data-activate]").forEach(b=>b.addEventListener("click",async()=>{try{const r=await api(`/api/usuarios/${b.dataset.activate}/ativar`,{method:"POST",body:JSON.stringify({})});toast(r.mensagem);await users();}catch(e){toast(e.message,"error");}}));
    $$("[data-reset]").forEach(b=>b.addEventListener("click",async()=>{
      if(!await confirmar("Redefinir senha","Será criada uma senha provisória; o usuário terá de trocá-la no próximo acesso.","Redefinir"))return;
      try{
        const r=await api(`/api/usuarios/${b.dataset.reset}/redefinir-senha`,{method:"POST",body:JSON.stringify({})});
        modal("Senha provisória",`<p>Informe esta senha ao usuário. Ela aparece <strong>somente agora</strong>.</p><p><code class="segredo" id="senha-provisoria">${esc(r.senha_provisoria)}</code></p><div class="form-actions"><button type="button" class="btn btn-secondary" id="copiar-senha">Copiar</button><button type="button" class="btn btn-primary" data-close>Fechar</button></div>`);
        $("#copiar-senha").onclick=async()=>{try{await navigator.clipboard.writeText(r.senha_provisoria);toast("Senha copiada.");}catch{toast("Não foi possível copiar. Anote a senha.","error");}};
      }catch(e){toast(e.message,"error");}
    }));
    $$("[data-disable]").forEach(b=>b.addEventListener("click",async()=>{if(!await confirmar("Desativar usuário","O usuário perde o acesso imediatamente.","Desativar",true))return;try{await api(`/api/usuarios/${b.dataset.disable}/desativar`,{method:"POST",body:JSON.stringify({})});toast("Usuário desativado.");await users();}catch(e){toast(e.message,"error");}}));
  }

  P.telas.usuarios = users;
})();
