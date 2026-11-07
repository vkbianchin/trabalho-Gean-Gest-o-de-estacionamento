/* Tela: login (senha e, quando ativada, verificação em duas etapas) */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { api, fd, trocarPagina } = P;
  const $ = P.$;

  // Esconde o olho nativo do Edge/Windows, já que a tela tem o botão "Mostrar".
  function esconderOlhoNativo() {
    if (document.getElementById("estilo-sem-olho-nativo")) return;
    const estilo = document.createElement("style");
    estilo.id = "estilo-sem-olho-nativo";
    estilo.textContent = 'input[type="password"]::-ms-reveal, input[type="password"]::-ms-clear { display: none; }';
    document.head.appendChild(estilo);
  }

  // Botão Mostrar/Ocultar: troca o tipo do campo entre "password" e "text".
  function ativarMostrarSenha() {
    document.querySelectorAll("[data-toggle-password]").forEach(botao => {
      const campo = document.getElementById(botao.dataset.togglePassword);
      if (!campo) return;
      botao.setAttribute("aria-controls", campo.id);
      botao.setAttribute("aria-pressed", "false");
      botao.addEventListener("click", () => {
        const mostrando = campo.type === "text";
        const inicio = campo.selectionStart, fim = campo.selectionEnd;
        campo.type = mostrando ? "password" : "text";
        botao.textContent = mostrando ? "Mostrar" : "Ocultar";
        botao.setAttribute("aria-pressed", String(!mostrando));
        campo.focus();
        try { campo.setSelectionRange(inicio, fim); } catch { /* ignora */ }
      });
    });
  }

  async function login(){
    esconderOlhoNativo();
    ativarMostrarSenha();

    const form = $("#login-form");
    let etapa = "senha";
    form?.addEventListener("submit", async e => {
      e.preventDefault();
      const erro = $("#login-error"), botao = form.querySelector('[type="submit"]');
      erro.textContent = "";
      botao.disabled = true;
      try {
        const r = await api(etapa === "senha" ? "/api/login" : "/api/login/2fa", { method: "POST", body: JSON.stringify(fd(form)) });
        if (r.exige_2fa) { etapa = "codigo"; pedirCodigo(form, botao); return; }
        trocarPagina(r.proxima || "/");
      } catch (ex) {
        erro.textContent = ex.message;
      } finally {
        botao.disabled = false;
      }
    });
    const senha = $("#login-password");
    senha?.addEventListener("keyup", e => { $("#caps-warning").hidden = !e.getModifierState("CapsLock"); });
  }

  function pedirCodigo(form, botao) {
    // Senha correta: esconde login e senha e pede o código de 6 dígitos do aplicativo autenticador.
    [...form.querySelectorAll("label")].filter(l => l.id !== "campo-codigo").forEach(l => { l.hidden = true; });
    form.elements.login.required = false;
    form.elements.senha.required = false;
    const campo = $("#campo-codigo");
    campo.hidden = false;
    form.elements.codigo.required = true;
    form.elements.codigo.focus();
    botao.firstChild.textContent = "Verificar código ";
  }

  P.telas.login = login;
})();
