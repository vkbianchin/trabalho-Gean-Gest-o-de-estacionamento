from flask import Blueprint, redirect, render_template, session

from ..erros import ErroNegocio
from ..permissoes import PERMISSOES

bp = Blueprint("paginas", __name__)
PAGINAS = {
    "/": "index.html", "/movimentacoes": "movimentacoes.html", "/login": "login.html", "/trocar-senha": "trocar_senha.html",
    "/caixa": "caixa.html", "/clientes": "clientes.html", "/veiculos": "veiculos.html", "/catalogos": "catalogos.html",
    "/vagas": "vagas.html", "/contratos": "contratos.html", "/pagamentos": "pagamentos.html", "/historico": "historico.html",
    "/configuracoes": "configuracoes.html", "/usuarios": "usuarios.html", "/auditoria": "auditoria.html",
    "/financeiro": "financeiro.html", "/relatorios": "relatorios.html", "/seguranca": "seguranca.html",
}
# Páginas exclusivas de administrador: usam a mesma tabela de permissões das APIs.
PAGINAS_PERMISSAO = {
    "/contratos": "contratos", "/configuracoes": "configuracoes", "/usuarios": "usuarios", "/auditoria": "auditoria",
    "/financeiro": "financeiro", "/relatorios": "relatorios",
}


@bp.get("/")
def raiz():
    if not session.get("usuario_id"):
        return redirect("/login")
    if session.get("trocar_senha"):
        return redirect("/trocar-senha")
    return render_template("index.html", pagina="painel")


@bp.get("/login")
def entrar():
    # Quem já está autenticado não vê a tela de login de novo (nem pelo botão "voltar").
    if session.get("usuario_id"):
        return redirect("/trocar-senha" if session.get("trocar_senha") else "/")
    return render_template("login.html", pagina="login")


@bp.get("/<path:caminho>")
def pagina(caminho):
    rota = "/" + caminho
    if rota not in PAGINAS:
        return render_template("erro.html", mensagem="Página não encontrada."), 404
    if not session.get("usuario_id"):
        return redirect("/login")
    if session.get("trocar_senha") and rota != "/trocar-senha":
        return redirect("/trocar-senha")
    permissao = PAGINAS_PERMISSAO.get(rota)
    if permissao and session.get("nivel_acesso") not in PERMISSOES[permissao]:
        raise ErroNegocio("Você não tem permissão para acessar esta página.", 403)
    return render_template(PAGINAS[rota], pagina=PAGINAS[rota][:-5])
