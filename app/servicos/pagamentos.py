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

def gerar_mensalidades(uid, referencia=None):
    """Gera cobranças do mês corrente para contratos vigentes; pode ser executado novamente."""
    from datetime import date
    hoje=referencia or date.today()
    competencia=date(hoje.year,hoje.month,1)
    cur=conexao().cursor(dictionary=True)
    cur.execute("SELECT id,valor_mensal,dia_vencimento,data_inicio FROM contratos_mensalistas WHERE data_fim IS NULL AND data_inicio<=%s",(hoje,)); contratos=cur.fetchall(); cur.close()
    conn=conexao(); criadas=0
    with transacao():
        cur=conn.cursor()
        for c in contratos:
            vencimento=date(hoje.year,hoje.month,min(c["dia_vencimento"],28))
            cur.execute("INSERT IGNORE INTO pagamentos (contrato_id,competencia,vencimento,valor,situacao,criado_por) VALUES (%s,%s,%s,%s,'aberto',%s)",(c["id"],competencia,vencimento,c["valor_mensal"],uid))
            criadas+=cur.rowcount
        cur.close()
    return {"criadas":criadas,"competencia":competencia.isoformat()}
