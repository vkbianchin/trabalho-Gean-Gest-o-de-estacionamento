from flask import Blueprint, jsonify, request

from ..erros import ErroNegocio
from ..permissoes import exigir
from ..servicos import financeiro
from ..tempo import hoje
from ..validadores import intervalo_iso

bp = Blueprint("financeiro", __name__)


def periodo_da_requisicao():
    """Lê ?inicio=&fim= (AAAA-MM-DD). Sem parâmetros, usa o mês corrente até hoje."""
    atual = hoje()
    inicio = request.args.get("inicio") or atual.replace(day=1).isoformat()
    fim = request.args.get("fim") or atual.isoformat()
    try:
        ini, final = intervalo_iso(inicio, fim)
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    return ini, final


@bp.get("/api/financeiro/resumo")
@exigir("financeiro")
def resumo():
    ini, fim = periodo_da_requisicao()
    return jsonify(financeiro.resumo(ini, fim))


@bp.get("/api/financeiro/inadimplencia")
@exigir("financeiro")
def inadimplencia():
    return jsonify(financeiro.inadimplencia())


@bp.get("/api/financeiro/caixas")
@exigir("financeiro")
def caixas():
    ini, fim = periodo_da_requisicao()
    return jsonify(financeiro.caixas_do_periodo(ini, fim))
