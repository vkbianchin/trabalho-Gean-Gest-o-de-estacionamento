from flask import Blueprint, redirect, render_template, request, session

from ..permissoes import PERMISSOES
from ..erros import ErroNegocio
from ..servicos import recibos

bp = Blueprint("recibos", __name__)


@bp.get("/recibo/pagamento/<int:pagamento_id>")
def recibo(pagamento_id):
    """Recibo imprimível (a impressão em PDF é feita pelo próprio navegador)."""
    if not session.get("usuario_id"):
        return redirect("/login")
    if session.get("nivel_acesso") not in PERMISSOES["operacao"]:
        raise ErroNegocio("Você não tem permissão para esta ação.", 403)
    dados = recibos.montar_recibo(pagamento_id, request.args.get("documento"))
    return render_template("recibo.html", **dados)
