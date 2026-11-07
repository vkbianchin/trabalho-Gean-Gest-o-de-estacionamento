"""Dados do recibo de pagamento (documento simples, sem valor fiscal)."""
from ..db import conexao
from ..erros import ErroNegocio
from ..tempo import formatar_duracao, minutos_entre
from ..validadores import documento_livre, formatar_documento
from . import configuracoes

ROTULOS_FORMA = {"dinheiro": "Dinheiro", "pix": "Pix", "cartao_debito": "Cartão de débito", "cartao_credito": "Cartão de crédito"}


def montar_recibo(pagamento_id, documento_informado=None):
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT p.id, p.valor, p.situacao, p.forma_pagamento, p.pago_em, p.competencia, p.movimentacao_id, p.contrato_id, "
            "m.placa AS placa_mov, m.entrada_em, m.saida_em, vg.numero AS vaga_numero, c.nome AS cliente_nome, c.documento AS cliente_documento, "
            "cv.placa AS placa_contrato, u.nome AS atendente FROM pagamentos p "
            "LEFT JOIN movimentacoes m ON m.id=p.movimentacao_id LEFT JOIN vagas vg ON vg.id=m.vaga_id "
            "LEFT JOIN contratos_mensalistas cm ON cm.id=p.contrato_id LEFT JOIN clientes c ON c.id=cm.cliente_id "
            "LEFT JOIN veiculos cv ON cv.id=cm.veiculo_id LEFT JOIN usuarios u ON u.id=COALESCE(p.atualizado_por, p.criado_por) "
            "WHERE p.id=%s", (pagamento_id,))
        p = cur.fetchone()
    finally:
        cur.close()
    if not p:
        raise ErroNegocio("Pagamento não encontrado.", 404)
    if p["situacao"] != "pago":
        raise ErroNegocio("Só é possível emitir recibo de um pagamento já recebido.")
    estabelecimento = configuracoes.obter()
    documento = p["cliente_documento"]
    if not documento and documento_informado:
        try:
            documento = documento_livre(documento_informado)
        except ValueError as exc:
            raise ErroNegocio(str(exc))
    minutos = minutos_entre(p["entrada_em"], p["saida_em"]) if p["entrada_em"] and p["saida_em"] else None
    return {
        "numero": p["id"],
        "estabelecimento": {"nome": estabelecimento.get("razao_social") or estabelecimento.get("nome_estacionamento"),
                            "cnpj": formatar_documento(estabelecimento["cnpj"]) if estabelecimento.get("cnpj") else None,
                            "endereco": estabelecimento.get("endereco"), "telefone": estabelecimento.get("telefone")},
        "mensalidade": p["contrato_id"] is not None,
        "cliente": p["cliente_nome"] or "Cliente horista",
        "documento": formatar_documento(documento) if documento else None,
        "placa": p["placa_contrato"] or p["placa_mov"],
        "competencia": p["competencia"], "vaga": p["vaga_numero"],
        "entrada_em": p["entrada_em"], "saida_em": p["saida_em"],
        "permanencia": formatar_duracao(minutos) if minutos is not None else None,
        "valor": p["valor"], "forma": ROTULOS_FORMA.get(p["forma_pagamento"], p["forma_pagamento"] or "—"),
        "pago_em": p["pago_em"], "atendente": p["atendente"],
    }
