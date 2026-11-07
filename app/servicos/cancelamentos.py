"""Cancelamento de movimentações e estorno de pagamentos (sempre com motivo e auditoria)."""
from ..auditoria import registrar as registrar_auditoria
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..tempo import agora
from ..validadores import texto


def _motivo(valor):
    try:
        return texto(valor, "motivo", 5, 200)
    except ValueError as exc:
        raise ErroNegocio(str(exc))


def cancelar_movimentacao(movimentacao_id, motivo, uid):
    """Cancela uma entrada lançada por engano (ou uma passagem já encerrada sem pagamento recebido).

    Entrada ainda aberta: a vaga é liberada (saída = entrada, valor zero). A linha continua no histórico,
    marcada como cancelada, e fica fora de relatórios e financeiro.
    """
    motivo = _motivo(motivo)
    conn = conexao()
    with transacao():
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id,placa,saida_em,valor_cobrado,cancelada FROM movimentacoes WHERE id=%s FOR UPDATE", (movimentacao_id,))
        m = cur.fetchone()
        if not m:
            cur.close()
            raise ErroNegocio("Movimentação não encontrada.", 404)
        if m["cancelada"]:
            cur.close()
            raise ErroNegocio("Esta movimentação já foi cancelada.", 409)
        cur.execute("SELECT COUNT(*) AS n FROM pagamentos WHERE movimentacao_id=%s AND situacao='pago'", (movimentacao_id,))
        if cur.fetchone()["n"]:
            cur.close()
            raise ErroNegocio("Esta passagem tem pagamento recebido. Estorne o pagamento antes de cancelar a movimentação.")
        agora_ = agora()
        base = "cancelada=1, cancelada_por=%s, cancelada_em=%s, motivo_cancelamento=%s, atualizado_por=%s"
        if m["saida_em"] is None:
            sql = f"UPDATE movimentacoes SET {base}, saida_em=entrada_em, valor_cobrado=0 WHERE id=%s"
        else:
            sql = f"UPDATE movimentacoes SET {base} WHERE id=%s"
        cur.execute(sql, (uid, agora_, motivo, uid, movimentacao_id))
        registrar_auditoria("movimentacoes", movimentacao_id, "cancelou", uid,
                            {"placa": m["placa"], "cancelada": 0, "valor_cobrado": m["valor_cobrado"]},
                            {"cancelada": 1, "motivo": motivo})
        cur.close()
    return {"mensagem": "Movimentação cancelada."}


def cancelar_pagamento(pagamento_id, motivo, uid):
    """Estorna um recebimento.

    - Mensalidade paga: volta para "aberto" e pode ser recebida de novo.
    - Pagamento de horista, ou mensalidade ainda em aberto: fica "cancelado".
    Recebimentos de um caixa já fechado não são alterados (mudariam um fechamento que já foi conferido).
    """
    motivo = _motivo(motivo)
    conn = conexao()
    with transacao():
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT p.id,p.situacao,p.valor,p.contrato_id,p.forma_pagamento,p.caixa_id,cx.fechado_em FROM pagamentos p LEFT JOIN caixas cx ON cx.id=p.caixa_id WHERE p.id=%s FOR UPDATE", (pagamento_id,))
        p = cur.fetchone()
        if not p:
            cur.close()
            raise ErroNegocio("Pagamento não encontrado.", 404)
        if p["situacao"] == "cancelado":
            cur.close()
            raise ErroNegocio("Este pagamento já está cancelado.", 409)
        if p["situacao"] == "pago" and p["caixa_id"] and p["fechado_em"] is not None:
            cur.close()
            raise ErroNegocio("O caixa em que este valor foi recebido já está fechado. O estorno alteraria um fechamento já conferido; trate o ajuste com o responsável financeiro.")
        agora_ = agora()
        if p["situacao"] == "pago" and p["contrato_id"] is not None:
            cur.execute("UPDATE pagamentos SET situacao='aberto',forma_pagamento=NULL,pago_em=NULL,caixa_id=NULL,atualizado_por=%s WHERE id=%s", (uid, pagamento_id))
            acao, final = "estornou", "aberto"
        else:
            cur.execute("UPDATE pagamentos SET situacao='cancelado',cancelado_por=%s,cancelado_em=%s,motivo_cancelamento=%s,atualizado_por=%s WHERE id=%s", (uid, agora_, motivo, uid, pagamento_id))
            acao, final = "cancelou", "cancelado"
        registrar_auditoria("pagamentos", pagamento_id, acao, uid,
                            {"situacao": p["situacao"], "valor": p["valor"], "forma_pagamento": p["forma_pagamento"]},
                            {"situacao": final, "motivo": motivo})
        cur.close()
    return {"mensagem": "Pagamento estornado; a mensalidade voltou para em aberto." if final == "aberto" else "Pagamento cancelado.",
            "situacao": final}
