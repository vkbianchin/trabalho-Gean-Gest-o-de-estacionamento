/* Tela: trocar_senha */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { toast, api, fd, catchForm, trocarPagina } = P;
  const $ = P.$;

  async function changePassword(){
    const pass=$("#new-password");pass?.addEventListener("input",()=>{const v=pass.value;const tests={length:v.length>=8,letters:/[A-Za-zÀ-ÿ]/.test(v),number:/\d/.test(v)};Object.entries(tests).forEach(([k,ok])=>{const el=$(`[data-rule="${k}"]`);if(el){el.classList.toggle("valid",ok);el.textContent=(ok?"✓ ":"○ ")+({length:"Pelo menos 8 caracteres",letters:"Contém letras",number:"Contém números"}[k]);}});});
    catchForm($("#change-password-form"),async e=>{const d=fd(e.currentTarget);if(d.nova_senha!==d.confirmacao)throw new Error("A confirmação da senha não corresponde.");delete d.confirmacao;const r=await api("/api/trocar-senha",{method:"POST",body:JSON.stringify(d)});toast(r.mensagem||"Senha alterada.");trocarPagina("/");});
  }

  P.telas.trocar_senha = changePassword;
})();
