/* Tela: segurança da conta (verificação em duas etapas) */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { api, catchForm, esc, fd, field, modal, panel, toast, confirmar } = P;
  const $ = P.$;

  const agrupar = segredo => String(segredo).replace(/(.{4})/g, "$1 ").trim();

  async function seguranca() {
    const { ativo } = await api("/api/2fa");
    $("#app-content").innerHTML =
      panel("Verificação em duas etapas", "Além da senha, o login passa a pedir um código de 6 dígitos gerado por um aplicativo autenticador (Google Authenticator, Microsoft Authenticator, Authy...).",
        ativo
          ? `<div class="notice notice-success">A verificação em duas etapas está <strong>ativa</strong> nesta conta.</div><form id="desativar-2fa" class="form-grid">${field("Senha atual","senha","password",true,"",'autocomplete="current-password"')}${field("Código do aplicativo","codigo","text",true,"000000",'inputmode="numeric" maxlength="7" autocomplete="one-time-code"')}<div class="form-actions span-2"><button class="btn btn-danger">Desativar verificação em duas etapas</button></div></form>`
          : `<div class="notice notice-warning">A verificação em duas etapas está <strong>desativada</strong>. Recomendamos ativar, principalmente para administradores.</div><div id="area-2fa"><button class="btn btn-primary" id="iniciar-2fa">Ativar verificação em duas etapas</button></div>`)
      + panel("Senha", "Troque a senha periodicamente e nunca a compartilhe.", `<a class="btn btn-secondary" href="/trocar-senha">Trocar senha</a>`);

    $("#iniciar-2fa")?.addEventListener("click", async () => {
      try {
        const d = await api("/api/2fa/iniciar", { method: "POST", body: JSON.stringify({}) });
        $("#area-2fa").innerHTML = `<ol class="passos"><li>No aplicativo autenticador, escolha <strong>adicionar conta</strong> e depois <strong>inserir chave de configuração</strong> (ou toque no link abaixo no celular).</li><li>Informe esta chave: <code class="segredo">${esc(agrupar(d.segredo))}</code> (tipo de chave: baseada em tempo).</li><li>Digite o código de 6 dígitos que o aplicativo mostrar:</li></ol><p><a href="${esc(d.uri)}">Abrir no aplicativo autenticador</a></p><form id="confirmar-2fa" class="form-grid">${field("Código de 6 dígitos","codigo","text",true,"000000",'inputmode="numeric" maxlength="7" autocomplete="one-time-code"')}<div class="form-actions span-2"><button class="btn btn-primary">Confirmar e ativar</button></div></form><small>Guarde a chave em local seguro: sem o aplicativo e sem a chave, o acesso só volta com ajuda de outro administrador.</small>`;
        catchForm($("#confirmar-2fa"), async e => {
          const r = await api("/api/2fa/confirmar", { method: "POST", body: JSON.stringify(fd(e.currentTarget)) });
          toast(r.mensagem);
          await seguranca();
        });
      } catch (err) { toast(err.message, "error"); }
    });

    const desativar = $("#desativar-2fa");
    if (desativar) catchForm(desativar, async e => {
      if (!await confirmar("Desativar verificação em duas etapas", "A conta voltará a usar apenas a senha para entrar.", "Desativar", true)) return;
      const r = await api("/api/2fa/desativar", { method: "POST", body: JSON.stringify(fd(e.currentTarget)) });
      toast(r.mensagem);
      await seguranca();
    });
  }

  P.telas.seguranca = seguranca;
})();
