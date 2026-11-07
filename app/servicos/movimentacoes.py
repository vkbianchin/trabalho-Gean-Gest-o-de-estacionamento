from datetime import datetime
from decimal import Decimal
from mysql.connector.errors import IntegrityError
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..validadores import placa
from ..cobranca import calcular_cobranca
from ..tempo import agora, formatar_duracao, hoje, minutos_entre, dias_em_atraso
from . import configuracoes

def consultar_placa(valor):
    try: p = placa(valor)
    except ValueError as exc: raise ErroNegocio(str(exc))
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT m.*,v.numero AS vaga_numero,p.nome AS plano_nome,t.nome AS tipo_nome FROM movimentacoes m JOIN vagas v ON v.id=m.vaga_id JOIN planos p ON p.id=m.plano_id JOIN tipos_veiculo t ON t.id=m.tipo_veiculo_id WHERE m.placa=%s AND m.saida_em IS NULL AND m.cancelada=0", (p,))
    aberta = cur.fetchone()
    cur.execute("SELECT v.id AS veiculo_id,v.tipo_veiculo_id,c.id AS cliente_id,c.nome AS cliente_nome,cm.id AS contrato_id,cm.valor_mensal,cm.data_inicio,cm.dia_vencimento FROM veiculos v JOIN clientes c ON c.id=v.cliente_id JOIN contratos_mensalistas cm ON cm.veiculo_id=v.id AND cm.data_fim IS NULL WHERE v.placa=%s AND v.ativo=1 AND c.ativo=1", (p,))
    mensalista = cur.fetchone()
    if mensalista:
        mensalista["em_atraso"] = _mensalidades_em_atraso(cur, mensalista["contrato_id"])
    cur.close()
    return {"placa":p,"movimentacao_aberta":aberta,"mensalista":mensalista}

def _mensalidades_em_atraso(cur, contrato_id):
    """Resumo das mensalidades vencidas e não pagas (já descontada a carência configurada)."""
    carencia = configuracoes.carencia_atraso()
    referencia = hoje()
    cur.execute("SELECT vencimento,valor FROM pagamentos WHERE contrato_id=%s AND situacao='aberto' AND vencimento IS NOT NULL ORDER BY vencimento", (contrato_id,))
    vencidas = [r for r in cur.fetchall() if dias_em_atraso(r["vencimento"], referencia, carencia) > 0]
    if not vencidas: return None
    return {"quantidade": len(vencidas), "total": str(sum((Decimal(str(r["valor"])) for r in vencidas), Decimal("0.00"))),
            "mais_antigo": vencidas[0]["vencimento"], "dias": dias_em_atraso(vencidas[0]["vencimento"], referencia, carencia)}

def escolher_vaga(vagas, ocupadas, vaga_id=None):
    """vagas: vagas ativas compatíveis (tipo e plano), ordenadas por número.
    ocupadas: conjunto de ids de vagas com movimentação aberta.
    Sem vaga_id escolhe a livre de menor número; com vaga_id valida a vaga pedida."""
    if vaga_id is not None:
        escolhida = next((v for v in vagas if v["id"] == vaga_id), None)
        if not escolhida: raise ErroNegocio("A vaga selecionada não existe ou não é compatível com este veículo.")
        if escolhida["id"] in ocupadas: raise ErroNegocio("A vaga selecionada já está ocupada.")
        return escolhida
    livre = next((v for v in vagas if v["id"] not in ocupadas), None)
    if not livre: raise ErroNegocio("Não há vaga livre disponível para esse veículo e plano.")
    return livre

def registrar_entrada(valor_placa, tipo_veiculo_id, uid, vaga_id=None, retroativa=False, entrada_em=None):
    try: p=placa(valor_placa)
    except ValueError as exc: raise ErroNegocio(str(exc))
    try: tipo=int(tipo_veiculo_id)
    except (TypeError, ValueError): raise ErroNegocio("Informe o tipo de veículo.")
    try: vaga_id=int(vaga_id) if vaga_id not in (None, "") else None
    except (TypeError, ValueError): raise ErroNegocio("Vaga inválida.")
    if retroativa and not entrada_em: raise ErroNegocio("Informe a data e hora da entrada retroativa.")
    entrada_em = entrada_em or agora()
    conn=conexao()
    cur=conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM movimentacoes WHERE placa=%s AND saida_em IS NULL AND cancelada=0", (p,))
        if cur.fetchone(): raise ErroNegocio("Este veículo já está estacionado.")
        # Só vale como mensalista com contrato vigente, veículo ativo e cliente ativo (igual à consulta de placa).
        cur.execute("SELECT v.id AS veiculo_id,v.tipo_veiculo_id,cm.id AS contrato_id FROM veiculos v JOIN clientes c ON c.id=v.cliente_id AND c.ativo=1 JOIN contratos_mensalistas cm ON cm.veiculo_id=v.id AND cm.data_fim IS NULL WHERE v.placa=%s AND v.ativo=1", (p,))
        mensalista=cur.fetchone()
        if mensalista and mensalista["tipo_veiculo_id"] != tipo: raise ErroNegocio("O tipo de veículo não corresponde ao cadastro do mensalista.")
        # Mensalista só ocupa vaga de plano mensal; horista, vaga de plano por hora. O plano vem da própria vaga.
        cur.execute("SELECT g.id, g.numero, g.plano_id FROM vagas g JOIN planos pl ON pl.id=g.plano_id WHERE g.ativo=1 AND g.tipo_veiculo_id=%s AND pl.cobranca=%s ORDER BY g.numero", (tipo, "mensal" if mensalista else "hora"))
        vagas=cur.fetchall()
        cur.execute("SELECT vaga_id FROM movimentacoes WHERE saida_em IS NULL AND cancelada=0")
        ocupadas={r["vaga_id"] for r in cur.fetchall()}
        escolhida=escolher_vaga(vagas, ocupadas, vaga_id)
        if not mensalista:
            cur.execute("SELECT valor FROM precos WHERE plano_id=%s AND tipo_veiculo_id=%s", (escolhida["plano_id"], tipo))
            preco=cur.fetchone()
            if not preco or preco["valor"] is None or preco["valor"] <= 0:
                raise ErroNegocio("Não há preço cadastrado para este plano e tipo de veículo. Cadastre em Catálogos > Preços.")
    finally:
        cur.close()
    try:
        with transacao():
            cur=conn.cursor()
            cur.execute("INSERT INTO movimentacoes (vaga_id,plano_id,tipo_veiculo_id,placa,veiculo_id,contrato_id,entrada_em,retroativa,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (escolhida["id"],escolhida["plano_id"],tipo,p,mensalista["veiculo_id"] if mensalista else None,mensalista["contrato_id"] if mensalista else None,entrada_em,int(retroativa),uid))
            mid=cur.lastrowid; cur.close()
    except IntegrityError as exc:
        if getattr(exc, "errno", None) == 1062:
            raise ErroNegocio("Outra entrada acabou de ocupar esta vaga ou esta placa. Atualize a tela e tente novamente.", 409)
        raise
    return {"id":mid,"placa":p,"vaga":escolhida["numero"],"mensalista":bool(mensalista)}

SQL_SAIDA = ("SELECT m.*,pl.cobranca,pl.nome AS plano_nome,pr.valor AS valor_hora,pr.valor_diaria,c.tolerancia_minutos,c.arredondamento,c.fracao_minutos,"
             "v.numero AS vaga_numero,t.nome AS tipo_nome FROM movimentacoes m JOIN planos pl ON pl.id=m.plano_id JOIN vagas v ON v.id=m.vaga_id "
             "JOIN tipos_veiculo t ON t.id=m.tipo_veiculo_id LEFT JOIN precos pr ON pr.plano_id=m.plano_id AND pr.tipo_veiculo_id=m.tipo_veiculo_id "
             "JOIN configuracoes c ON c.id=1 WHERE m.placa=%s AND m.saida_em IS NULL AND m.cancelada=0")

def _buscar_aberta(conn, p):
    cur = conn.cursor(dictionary=True)
    cur.execute(SQL_SAIDA, (p,))
    m = cur.fetchone(); cur.close()
    if not m: raise ErroNegocio("Não existe entrada aberta para esta placa.", 404)
    return m

def calcular_saida(m, saida_em):
    """Aplica as regras de cobrança a uma movimentação aberta (não grava nada)."""
    if saida_em < m["entrada_em"]: raise ErroNegocio("A saída não pode ser anterior à entrada.")
    minutos = minutos_entre(m["entrada_em"], saida_em)
    mensalista = m["cobranca"] == "mensal"
    if mensalista:
        valor = Decimal("0.00")
    else:
        if m["valor_hora"] is None: raise ErroNegocio("Não há preço cadastrado para este plano e tipo de veículo. Cadastre em Catálogos > Preços.")
        valor = calcular_cobranca(m["entrada_em"], saida_em, m["valor_hora"], m["tolerancia_minutos"], m["arredondamento"], m["fracao_minutos"], m["valor_diaria"])
    return {"minutos": minutos, "tempo": formatar_duracao(minutos), "valor": valor, "mensalista": mensalista}

def _resumo_saida(m, p, saida_em, calculo):
    return {"id": m["id"], "placa": p, "vaga": m["vaga_numero"], "plano": m["plano_nome"], "tipo_veiculo": m["tipo_nome"],
            "entrada_em": m["entrada_em"], "saida_em": saida_em, "tempo_minutos": calculo["minutos"], "tempo": calculo["tempo"],
            "valor": str(calculo["valor"]), "mensalista": calculo["mensalista"], "tolerancia_minutos": m["tolerancia_minutos"]}

def previa_saida(valor_placa):
    """Mostra permanência e valor que seriam cobrados agora, sem registrar a saída."""
    try: p = placa(valor_placa)
    except ValueError as exc: raise ErroNegocio(str(exc))
    m = _buscar_aberta(conexao(), p)
    saida_em = agora()
    calculo = calcular_saida(m, saida_em)
    resumo = _resumo_saida(m, p, saida_em, calculo)
    resumo["exige_pagamento"] = calculo["valor"] > 0
    return resumo

def registrar_saida(valor_placa, uid, caixa_id=None, forma_pagamento=None, retroativa=False, saida_em=None):
    try: p=placa(valor_placa)
    except ValueError as exc: raise ErroNegocio(str(exc))
    if retroativa and not saida_em: raise ErroNegocio("Informe a data e hora da saída retroativa.")
    saida_em=saida_em or agora()
    conn=conexao()
    m=_buscar_aberta(conn, p)
    calculo=calcular_saida(m, saida_em)
    valor=calculo["valor"]
    if valor > 0:
        if not caixa_id or not forma_pagamento: raise ErroNegocio("Informe o caixa aberto e a forma de pagamento.")
        cur=conn.cursor(dictionary=True); cur.execute("SELECT id FROM caixas WHERE id=%s AND usuario_id=%s AND fechado_em IS NULL", (caixa_id,uid)); caixa=cur.fetchone(); cur.close()
        if not caixa: raise ErroNegocio("Abra seu caixa antes de receber pagamentos.")
    pagamento_id=None
    with transacao():
        cur=conn.cursor()
        cur.execute("UPDATE movimentacoes SET saida_em=%s,valor_cobrado=%s,retroativa=%s,atualizado_por=%s WHERE id=%s AND saida_em IS NULL AND cancelada=0", (saida_em,valor,int(retroativa),uid,m["id"]))
        if cur.rowcount != 1: cur.close(); raise ErroNegocio("A movimentação já foi encerrada. Atualize a consulta.",409)
        if m["cobranca"]=="hora" and valor>0:
            cur.execute("INSERT INTO pagamentos (movimentacao_id,valor,situacao,forma_pagamento,pago_em,caixa_id,criado_por) VALUES (%s,%s,'pago',%s,%s,%s,%s)", (m["id"],valor,forma_pagamento,saida_em,caixa_id,uid))
            pagamento_id=cur.lastrowid
        cur.close()
    resumo=_resumo_saida(m, p, saida_em, calculo)
    resumo.update({"forma_pagamento": forma_pagamento if valor>0 else None, "pagamento_id": pagamento_id})
    return resumo

def historico_placa(valor_placa, limite=500):
    """Todas as passagens de uma placa (da mais recente para a mais antiga) com totais."""
    try: p = placa(valor_placa)
    except ValueError as exc: raise ErroNegocio(str(exc))
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT m.*,v.numero AS vaga_numero,pl.nome AS plano_nome,t.nome AS tipo_nome,u.nome AS operador FROM movimentacoes m JOIN vagas v ON v.id=m.vaga_id JOIN planos pl ON pl.id=m.plano_id JOIN tipos_veiculo t ON t.id=m.tipo_veiculo_id LEFT JOIN usuarios u ON u.id=m.criado_por WHERE m.placa=%s ORDER BY m.entrada_em DESC LIMIT %s", (p, int(limite)))
    linhas = cur.fetchall()
    cur.execute("SELECT v.id,v.placa,c.nome AS cliente_nome,t.nome AS tipo_nome,mo.nome AS modelo,co.nome AS cor FROM veiculos v JOIN clientes c ON c.id=v.cliente_id JOIN tipos_veiculo t ON t.id=v.tipo_veiculo_id LEFT JOIN modelos mo ON mo.id=v.modelo_id LEFT JOIN cores co ON co.id=v.cor_id WHERE v.placa=%s", (p,))
    cadastro = cur.fetchone()
    cur.close()
    return montar_historico(p, linhas, cadastro)

def montar_historico(p, linhas, cadastro=None):
    """Transforma as linhas do banco em histórico + totais (função pura, testável sem banco)."""
    passagens = []
    for r in linhas:
        cancelada = bool(r.get("cancelada"))
        minutos = minutos_entre(r["entrada_em"], r["saida_em"]) if r.get("saida_em") else None
        passagens.append({"id": r["id"], "entrada_em": r["entrada_em"], "saida_em": r.get("saida_em"), "vaga": r["vaga_numero"],
                          "plano": r["plano_nome"], "tipo_veiculo": r["tipo_nome"], "valor": r.get("valor_cobrado"),
                          "minutos": minutos, "tempo": formatar_duracao(minutos) if minutos is not None else None,
                          "operador": r.get("operador"), "cancelada": cancelada, "retroativa": bool(r.get("retroativa")),
                          "no_local": r.get("saida_em") is None and not cancelada})
    validas = [x for x in passagens if not x["cancelada"]]
    concluidas = [x for x in validas if x["minutos"] is not None]
    total = sum((Decimal(str(x["valor"])) for x in validas if x["valor"] is not None), Decimal("0.00"))
    total_minutos = sum(x["minutos"] for x in concluidas)
    return {"placa": p, "cadastro": cadastro, "passagens": passagens,
            "totais": {"visitas": len(validas), "no_local": sum(1 for x in validas if x["no_local"]), "total_gasto": str(total),
                       "tempo_total": formatar_duracao(total_minutos), "tempo_medio": formatar_duracao(total_minutos // len(concluidas)) if concluidas else None,
                       "primeira_visita": validas[-1]["entrada_em"] if validas else None, "ultima_visita": validas[0]["entrada_em"] if validas else None}}
