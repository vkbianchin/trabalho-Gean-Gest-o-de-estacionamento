"""Relatórios operacionais com exportação em CSV."""
from ..db import conexao
from ..tempo import formatar_duracao, limites_do_periodo, minutos_entre

LIMITE_LINHAS = 5000
DIAS_SEMANA = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]

COLUNAS_MOVIMENTACOES = [("id", "Nº"), ("placa", "Placa"), ("tipo_veiculo", "Tipo"), ("plano", "Plano"), ("vaga", "Vaga"),
                         ("entrada_em", "Entrada"), ("saida_em", "Saída"), ("tempo", "Permanência"), ("valor", "Valor cobrado"),
                         ("operador", "Operador")]
COLUNAS_RECEBIMENTOS = [("id", "Nº"), ("pago_em", "Pago em"), ("origem", "Origem"), ("cliente", "Cliente"), ("placa", "Placa"),
                        ("competencia", "Competência"), ("forma_pagamento", "Forma"), ("valor", "Valor"), ("caixa_id", "Caixa")]


def _linhas(sql, params=()):
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()


def movimentacoes(inicio, fim):
    ini, lim = limites_do_periodo(inicio, fim)
    linhas = _linhas(
        "SELECT m.id, m.placa, m.entrada_em, m.saida_em, m.valor_cobrado AS valor, v.numero AS vaga, pl.nome AS plano, "
        "t.nome AS tipo_veiculo, u.nome AS operador FROM movimentacoes m JOIN vagas v ON v.id=m.vaga_id "
        "JOIN planos pl ON pl.id=m.plano_id JOIN tipos_veiculo t ON t.id=m.tipo_veiculo_id LEFT JOIN usuarios u ON u.id=m.criado_por "
        "WHERE m.cancelada = 0 AND m.entrada_em >= %s AND m.entrada_em < %s ORDER BY m.entrada_em DESC LIMIT %s", (ini, lim, LIMITE_LINHAS))
    for linha in linhas:
        minutos = minutos_entre(linha["entrada_em"], linha["saida_em"]) if linha["saida_em"] else None
        linha["tempo"] = formatar_duracao(minutos) if minutos is not None else "no local"
    return linhas


def recebimentos(inicio, fim):
    ini, lim = limites_do_periodo(inicio, fim)
    linhas = _linhas(
        "SELECT p.id, p.pago_em, p.valor, p.forma_pagamento, p.competencia, p.caixa_id, "
        "CASE WHEN p.contrato_id IS NOT NULL THEN 'Mensalidade' ELSE 'Horista' END AS origem, c.nome AS cliente, "
        "COALESCE(v.placa, m.placa) AS placa FROM pagamentos p LEFT JOIN contratos_mensalistas cm ON cm.id=p.contrato_id "
        "LEFT JOIN clientes c ON c.id=cm.cliente_id LEFT JOIN veiculos v ON v.id=cm.veiculo_id "
        "LEFT JOIN movimentacoes m ON m.id=p.movimentacao_id "
        "WHERE p.situacao='pago' AND p.pago_em >= %s AND p.pago_em < %s ORDER BY p.pago_em DESC LIMIT %s", (ini, lim, LIMITE_LINHAS))
    for linha in linhas:
        linha["cliente"] = linha["cliente"] or "Horista"
    return linhas


def ocupacao(inicio, fim):
    """Entradas por hora do dia e por dia da semana, para enxergar os horários de pico."""
    ini, lim = limites_do_periodo(inicio, fim)
    por_hora = _linhas("SELECT HOUR(entrada_em) AS chave, COUNT(*) AS entradas FROM movimentacoes WHERE cancelada = 0 AND entrada_em >= %s AND entrada_em < %s GROUP BY HOUR(entrada_em)", (ini, lim))
    por_dia = _linhas("SELECT DAYOFWEEK(entrada_em) AS chave, COUNT(*) AS entradas FROM movimentacoes WHERE cancelada = 0 AND entrada_em >= %s AND entrada_em < %s GROUP BY DAYOFWEEK(entrada_em)", (ini, lim))
    return distribuir(por_hora, por_dia)


def distribuir(por_hora, por_dia):
    """Completa com zero as horas (0-23) e dias da semana sem entradas (função pura, testável sem banco)."""
    horas = {int(r["chave"]): int(r["entradas"]) for r in por_hora}
    dias = {int(r["chave"]): int(r["entradas"]) for r in por_dia}  # DAYOFWEEK: 1 = domingo
    lista_horas = [{"hora": h, "rotulo": f"{h:02d}h", "entradas": horas.get(h, 0)} for h in range(24)]
    lista_dias = [{"dia": i + 1, "rotulo": nome, "entradas": dias.get(i + 1, 0)} for i, nome in enumerate(DIAS_SEMANA)]
    pico = max(lista_horas, key=lambda x: x["entradas"])
    return {"por_hora": lista_horas, "por_dia_semana": lista_dias,
            "total_entradas": sum(horas.values()), "hora_de_pico": pico["rotulo"] if pico["entradas"] else None}
