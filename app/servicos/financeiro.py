"""Indicadores financeiros do estacionamento: recebimentos, inadimplência e fechamentos de caixa."""
from decimal import Decimal

from ..db import conexao
from ..tempo import dias_em_atraso, hoje, limites_do_periodo
from . import configuracoes

ZERO = Decimal("0.00")


def _linhas(sql, params=()):
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()


def _dinheiro(valor):
    return str(Decimal(str(valor or 0)).quantize(ZERO))


def resumo(inicio, fim):
    """Totais do período [inicio, fim] (datas inclusivas) com base em pagamentos efetivamente recebidos."""
    ini, lim = limites_do_periodo(inicio, fim)
    pagos = "situacao='pago' AND pago_em >= %s AND pago_em < %s"
    geral = _linhas(f"SELECT COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS total FROM pagamentos WHERE {pagos}", (ini, lim))[0]
    por_forma = _linhas(f"SELECT forma_pagamento, COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS total FROM pagamentos WHERE {pagos} GROUP BY forma_pagamento ORDER BY total DESC", (ini, lim))
    por_origem = _linhas(f"SELECT CASE WHEN contrato_id IS NOT NULL THEN 'mensalidade' ELSE 'horista' END AS origem, COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS total FROM pagamentos WHERE {pagos} GROUP BY origem", (ini, lim))
    por_dia = _linhas(f"SELECT DATE(pago_em) AS dia, COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS total FROM pagamentos WHERE {pagos} GROUP BY DATE(pago_em) ORDER BY dia", (ini, lim))
    saidas = _linhas("SELECT COUNT(*) AS quantidade, COALESCE(AVG(TIMESTAMPDIFF(MINUTE, entrada_em, saida_em)),0) AS media_minutos FROM movimentacoes WHERE cancelada = 0 AND saida_em >= %s AND saida_em < %s", (ini, lim))[0]
    aberto = _linhas("SELECT COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS total FROM pagamentos WHERE situacao='aberto' AND contrato_id IS NOT NULL")[0]
    em_atraso = inadimplencia()
    horista = next((o for o in por_origem if o["origem"] == "horista"), {"quantidade": 0, "total": ZERO})
    ticket = Decimal(str(horista["total"])) / horista["quantidade"] if horista["quantidade"] else ZERO
    return {
        "periodo": {"inicio": inicio, "fim": fim},
        "total_recebido": _dinheiro(geral["total"]),
        "recebimentos": geral["quantidade"],
        "por_forma": [{**r, "total": _dinheiro(r["total"])} for r in por_forma],
        "por_origem": [{**r, "total": _dinheiro(r["total"])} for r in por_origem],
        "por_dia": [{**r, "total": _dinheiro(r["total"])} for r in por_dia],
        "saidas": saidas["quantidade"],
        "permanencia_media_minutos": int(saidas["media_minutos"] or 0),
        "ticket_medio_horista": _dinheiro(ticket),
        "a_receber": {"quantidade": aberto["quantidade"], "total": _dinheiro(aberto["total"])},
        "em_atraso": {"quantidade": len(em_atraso), "total": _dinheiro(sum((Decimal(str(i["valor"])) for i in em_atraso), ZERO))},
    }


def inadimplencia(referencia=None):
    """Mensalidades vencidas e não pagas, já descontada a carência configurada."""
    referencia = referencia or hoje()
    carencia = configuracoes.carencia_atraso()
    linhas = _linhas(
        "SELECT p.id, p.competencia, p.vencimento, p.valor, c.nome AS cliente_nome, c.telefone, v.placa "
        "FROM pagamentos p JOIN contratos_mensalistas cm ON cm.id=p.contrato_id JOIN clientes c ON c.id=cm.cliente_id "
        "JOIN veiculos v ON v.id=cm.veiculo_id WHERE p.situacao='aberto' AND p.vencimento IS NOT NULL ORDER BY p.vencimento")
    resultado = []
    for linha in linhas:
        dias = dias_em_atraso(linha["vencimento"], referencia, carencia)
        if dias > 0:
            resultado.append({**linha, "valor": _dinheiro(linha["valor"]), "dias_atraso": dias})
    return resultado


def caixas_do_periodo(inicio, fim):
    ini, lim = limites_do_periodo(inicio, fim)
    return _linhas(
        "SELECT cx.id, u.nome AS operador, cx.aberto_em, cx.fechado_em, cx.valor_inicial, cx.dinheiro_esperado, "
        "cx.dinheiro_contado, cx.diferenca, cx.observacao FROM caixas cx JOIN usuarios u ON u.id=cx.usuario_id "
        "WHERE cx.aberto_em >= %s AND cx.aberto_em < %s ORDER BY cx.aberto_em DESC LIMIT 200", (ini, lim))
