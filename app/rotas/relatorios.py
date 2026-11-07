from flask import Blueprint, Response, jsonify

from ..exportacao import gerar_csv
from ..permissoes import exigir
from ..servicos import relatorios
from .financeiro import periodo_da_requisicao

bp = Blueprint("relatorios", __name__)


def _resposta_csv(nome, colunas, linhas, ini, fim):
    arquivo = f"{nome}_{ini.isoformat()}_a_{fim.isoformat()}.csv"
    return Response(gerar_csv(colunas, linhas), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{arquivo}"'})


@bp.get("/api/relatorios/movimentacoes")
@exigir("relatorios")
def movimentacoes():
    ini, fim = periodo_da_requisicao()
    return jsonify(relatorios.movimentacoes(ini, fim))


@bp.get("/api/relatorios/movimentacoes.csv")
@exigir("relatorios")
def movimentacoes_csv():
    ini, fim = periodo_da_requisicao()
    return _resposta_csv("movimentacoes", relatorios.COLUNAS_MOVIMENTACOES, relatorios.movimentacoes(ini, fim), ini, fim)


@bp.get("/api/relatorios/recebimentos")
@exigir("relatorios")
def recebimentos():
    ini, fim = periodo_da_requisicao()
    return jsonify(relatorios.recebimentos(ini, fim))


@bp.get("/api/relatorios/recebimentos.csv")
@exigir("relatorios")
def recebimentos_csv():
    ini, fim = periodo_da_requisicao()
    return _resposta_csv("recebimentos", relatorios.COLUNAS_RECEBIMENTOS, relatorios.recebimentos(ini, fim), ini, fim)


@bp.get("/api/relatorios/ocupacao")
@exigir("relatorios")
def ocupacao():
    ini, fim = periodo_da_requisicao()
    return jsonify(relatorios.ocupacao(ini, fim))
