from decimal import Decimal
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..validadores import dinheiro
from ..tempo import agora

def caixa_aberto(uid):
    cur=conexao().cursor(dictionary=True); cur.execute("SELECT * FROM caixas WHERE usuario_id=%s AND fechado_em IS NULL",(uid,)); r=cur.fetchone(); cur.close(); return r

def abrir(uid, valor_inicial):
    try: valor=dinheiro(valor_inicial,"troco inicial")
    except ValueError as exc: raise ErroNegocio(str(exc))
    if caixa_aberto(uid): raise ErroNegocio("Você já possui um caixa aberto.")
    conn=conexao()
    with transacao():
        cur=conn.cursor(); cur.execute("INSERT INTO caixas (usuario_id,aberto_em,valor_inicial,criado_por) VALUES (%s,%s,%s,%s)",(uid,agora(),valor,uid)); cid=cur.lastrowid; cur.close()
    return {"id":cid,"valor_inicial":str(valor)}

def fechar(uid, dinheiro_contado, observacao=None):
    try: contado=dinheiro(dinheiro_contado,"dinheiro contado")
    except ValueError as exc: raise ErroNegocio(str(exc))
    caixa=caixa_aberto(uid)
    if not caixa: raise ErroNegocio("Não há caixa aberto para fechar.")
    cur=conexao().cursor(dictionary=True)
    cur.execute("SELECT COALESCE(SUM(valor),0) AS total FROM pagamentos WHERE caixa_id=%s AND situacao='pago' AND forma_pagamento='dinheiro'",(caixa["id"],)); pagamentos=Decimal(str(cur.fetchone()["total"])); cur.close()
    esperado=Decimal(str(caixa["valor_inicial"]))+pagamentos
    diferenca=contado-esperado
    conn=conexao()
    with transacao():
        cur=conn.cursor(); cur.execute("UPDATE caixas SET fechado_em=%s,dinheiro_esperado=%s,dinheiro_contado=%s,diferenca=%s,observacao=%s,atualizado_por=%s WHERE id=%s AND fechado_em IS NULL",(agora(),esperado,contado,diferenca,observacao,uid,caixa["id"])); cur.close()
    return {"dinheiro_esperado":str(esperado),"dinheiro_contado":str(contado),"diferenca":str(diferenca)}
