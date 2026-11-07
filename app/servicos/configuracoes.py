"""Configurações gerais do estacionamento (linha única id = 1 da tabela configuracoes)."""
from ..auditoria import registrar as registrar_auditoria
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..validadores import cnpj, telefone, texto

# Colunas criadas pela migração 004. Se ela ainda não foi aplicada, o sistema continua funcionando
# com os valores padrão e simplesmente não grava esses campos.
CAMPOS_ESTABELECIMENTO = ("razao_social", "cnpj", "endereco", "telefone", "dias_carencia_atraso")
PADRAO_CARENCIA = 0


def _ler():
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM configuracoes WHERE id=1")
        return cur.fetchone() or {}
    finally:
        cur.close()


def obter():
    linha = dict(_ler())
    for campo in CAMPOS_ESTABELECIMENTO:
        linha.setdefault(campo, None)
    linha["dias_carencia_atraso"] = int(linha.get("dias_carencia_atraso") or PADRAO_CARENCIA)
    return linha


def carencia_atraso():
    """Dias de tolerância depois do vencimento antes de a mensalidade contar como atrasada."""
    return obter()["dias_carencia_atraso"]


def _inteiro(valor, campo, minimo, maximo):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{campo.capitalize()} deve ser um número inteiro.")
    if not minimo <= numero <= maximo:
        raise ValueError(f"{campo.capitalize()} deve estar entre {minimo} e {maximo}.")
    return numero


def validar(d):
    """Valida os dados do formulário e devolve apenas o que pode ser gravado."""
    regra = d.get("arredondamento")
    if regra not in ("hora_cheia", "fracao"):
        raise ValueError("Regra de arredondamento inválida.")
    dados = {
        "nome_estacionamento": texto(d.get("nome_estacionamento"), "nome do estacionamento", 1, 80),
        "tolerancia_minutos": _inteiro(d.get("tolerancia_minutos"), "tolerância", 0, 1440),
        "fracao_minutos": _inteiro(d.get("fracao_minutos"), "fração", 1, 60),
        "arredondamento": regra,
    }
    razao = (d.get("razao_social") or "").strip()
    dados["razao_social"] = texto(razao, "razão social", 1, 150) if razao else None
    doc = str(d.get("cnpj") or "").strip()
    dados["cnpj"] = cnpj(doc) if doc else None
    endereco = (d.get("endereco") or "").strip()
    dados["endereco"] = texto(endereco, "endereço", 1, 200) if endereco else None
    fone = str(d.get("telefone") or "").strip()
    dados["telefone"] = telefone(fone) if fone else None
    dados["dias_carencia_atraso"] = _inteiro(d.get("dias_carencia_atraso", 0), "dias de carência", 0, 30)
    return dados


def _colunas_existentes():
    cur = conexao().cursor()
    try:
        cur.execute("SHOW COLUMNS FROM configuracoes")
        return {linha[0] for linha in cur.fetchall()}
    finally:
        cur.close()


def atualizar(d, uid):
    try:
        novos = validar(d)
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    existentes = _colunas_existentes()
    antes = _ler()
    # Só grava colunas que existem no banco (a migração 004 pode ainda não ter sido aplicada).
    colunas = [c for c in novos if c in existentes]
    ignoradas = [c for c in novos if c not in colunas]
    if not colunas:
        raise ErroNegocio("A tabela de configurações não tem as colunas esperadas. Confira o banco (banco/schema.sql).")
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        if antes:
            sql = "UPDATE configuracoes SET " + ", ".join(f"{c}=%s" for c in colunas) + ", atualizado_por=%s WHERE id=1"
            cur.execute(sql, [novos[c] for c in colunas] + [uid])
        else:
            # Primeira gravação: a tabela ainda não tem a linha única (id = 1), então ela é criada agora.
            nomes = ["id"] + colunas
            valores = [1] + [novos[c] for c in colunas]
            for extra in ("criado_por", "atualizado_por"):
                if extra in existentes:
                    nomes.append(extra)
                    valores.append(uid)
            sql = f"INSERT INTO configuracoes ({', '.join(nomes)}) VALUES ({', '.join(['%s'] * len(nomes))})"
            cur.execute(sql, valores)
        cur.close()
        registrar_auditoria("configuracoes", 1, "alterou" if antes else "criou", uid,
                            {c: antes.get(c) for c in colunas} if antes else None, {c: novos[c] for c in colunas})
    return {"mensagem": "Configurações atualizadas.", "campos_ignorados": ignoradas}
