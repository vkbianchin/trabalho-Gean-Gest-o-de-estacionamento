from datetime import date
from mysql.connector.errors import IntegrityError
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..servicos.caixa import caixa_aberto
from ..tempo import agora

FORMAS={"dinheiro","pix","cartao_debito","cartao_credito"}

def receber_mensalidade(pagamento_id, uid, forma):
    if forma not in FORMAS: raise ErroNegocio("Forma de pagamento inválida.")
    caixa=caixa_aberto(uid)
    if not caixa: raise ErroNegocio("Abra o caixa antes de receber pagamentos.")
    conn=conexao(); cur=conn.cursor(dictionary=True)
    cur.execute("SELECT id,valor,situacao,contrato_id FROM pagamentos WHERE id=%s AND contrato_id IS NOT NULL",(pagamento_id,)); p=cur.fetchone(); cur.close()
    if not p: raise ErroNegocio("Mensalidade não encontrada.",404)
    if p["situacao"]!="aberto": raise ErroNegocio("Somente pagamentos em aberto podem ser recebidos.")
    with transacao():
        cur=conn.cursor(); cur.execute("UPDATE pagamentos SET situacao='pago',forma_pagamento=%s,pago_em=%s,caixa_id=%s,atualizado_por=%s WHERE id=%s AND situacao='aberto'",(forma,agora(),caixa["id"],uid,pagamento_id));
        if cur.rowcount!=1: cur.close(); raise ErroNegocio("O pagamento foi alterado por outro processo.",409)
        cur.close()
    return {"id":pagamento_id,"valor":str(p["valor"]),"situacao":"pago"}

def _meses(inicio, fim):
    """Primeiro dia de cada mês, do mês de 'inicio' até o mês de 'fim' (inclusive)."""
    ano, mes = inicio.year, inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        yield date(ano, mes, 1)
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)

def competencias_devidas(data_inicio, dia_vencimento, hoje):
    """Cobranças devidas de um contrato vigente, do mês de início até o mês de 'hoje'.
    A primeira é o mês de início, em valor integral; o vencimento é o dia escolhido do mês,
    mas nunca antes da data de início do contrato."""
    if data_inicio > hoje: return []
    dia = min(int(dia_vencimento), 28)
    devidas = []
    for competencia in _meses(data_inicio, hoje):
        vencimento = max(date(competencia.year, competencia.month, dia), data_inicio)
        devidas.append((competencia, vencimento))
    return devidas

def gerar_mensalidades(uid, referencia=None):
    """Gera as cobranças devidas dos contratos vigentes (do mês de início até o mês atual).
    Pode ser executado novamente: o que já existe não é duplicado (cobranças canceladas não contam)."""
    hoje = referencia or agora().date()
    conn = conexao(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id,valor_mensal,dia_vencimento,data_inicio FROM contratos_mensalistas WHERE data_fim IS NULL AND data_inicio<=%s", (hoje,))
    contratos = cur.fetchall()
    cur.execute("SELECT contrato_id,competencia FROM pagamentos WHERE contrato_id IS NOT NULL AND situacao<>'cancelado'")
    existentes = {(r["contrato_id"], r["competencia"]) for r in cur.fetchall()}
    cur.close()
    criadas = ja_existiam = 0
    with transacao():
        cur = conn.cursor()
        for c in contratos:
            for competencia, vencimento in competencias_devidas(c["data_inicio"], c["dia_vencimento"], hoje):
                if (c["id"], competencia) in existentes:
                    ja_existiam += 1; continue
                try:
                    cur.execute("INSERT INTO pagamentos (contrato_id,competencia,vencimento,valor,situacao,criado_por) VALUES (%s,%s,%s,%s,'aberto',%s)", (c["id"], competencia, vencimento, c["valor_mensal"], uid))
                    criadas += 1
                except IntegrityError as exc:
                    if getattr(exc, "errno", None) != 1062: raise
                    ja_existiam += 1  # outra execução criou a mesma cobrança ao mesmo tempo
        cur.close()
    return {"criadas": criadas, "ja_existiam": ja_existiam, "contratos": len(contratos), "competencia": date(hoje.year, hoje.month, 1).isoformat()}
