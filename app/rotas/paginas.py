from flask import Blueprint, render_template, redirect, session
from ..erros import ErroNegocio
from ..permissoes import PERMISSOES
bp=Blueprint("paginas",__name__)
PAGINAS={"/":"index.html","/movimentacoes":"movimentacoes.html","/login":"login.html","/trocar-senha":"trocar_senha.html","/caixa":"caixa.html","/clientes":"clientes.html","/veiculos":"veiculos.html","/catalogos":"catalogos.html","/vagas":"vagas.html","/contratos":"contratos.html","/pagamentos":"pagamentos.html","/configuracoes":"configuracoes.html","/usuarios":"usuarios.html","/auditoria":"auditoria.html"}
# Páginas exclusivas de administrador: usam a mesma tabela de permissões das APIs.
PAGINAS_PERMISSAO={"/contratos":"contratos","/configuracoes":"configuracoes","/usuarios":"usuarios","/auditoria":"auditoria"}
@bp.get("/")
def raiz():
    if not session.get("usuario_id"): return redirect("/login")
    if session.get("trocar_senha"): return redirect("/trocar-senha")
    return render_template("index.html", pagina="painel")
@bp.get("/<path:caminho>")
def pagina(caminho):
    rota="/"+caminho
    if rota not in PAGINAS: return render_template("_em_construcao.html",mensagem="Página não encontrada."),404
    if rota!="/login" and not session.get("usuario_id"): return redirect("/login")
    if session.get("trocar_senha") and rota not in ("/trocar-senha","/login"): return redirect("/trocar-senha")
    permissao=PAGINAS_PERMISSAO.get(rota)
    if permissao and session.get("nivel_acesso") not in PERMISSOES[permissao]:
        raise ErroNegocio("Você não tem permissão para acessar esta página.",403)
    return render_template(PAGINAS[rota], pagina=PAGINAS[rota][:-5])
