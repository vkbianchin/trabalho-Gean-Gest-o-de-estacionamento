from ..db import conexao
from ..erros import ErroNegocio
from ..validadores import cpf, telefone, email, cep, texto, placa
from ..auditoria import registrar as registrar_auditoria
from mysql.connector.errors import IntegrityError
from decimal import Decimal

def listar_catalogo(tabela):
    permitidas = {"marcas", "tipos_veiculo", "modelos", "cores", "planos"}
    if tabela not in permitidas:
        raise ErroNegocio("Catálogo inválido.")
    return _todos(f"SELECT * FROM {tabela} ORDER BY nome")

def _todos(sql, params=()):
    cur = conexao().cursor(dictionary=True)
    cur.execute(sql, params)
    resultado = cur.fetchall()
    cur.close()
    return resultado

def criar_cliente(d, uid):
    try:
        valores = (texto(d.get("nome"),"nome",2,100), cpf(d.get("cpf")), telefone(d.get("telefone")), email(d.get("email")), cep(d.get("cep")), texto(d.get("logradouro"),"logradouro",1,150), texto(str(d.get("numero", "")),"número",1,10), texto(d["complemento"],"complemento",0,60) if d.get("complemento") else None, texto(d.get("bairro"),"bairro",1,80), texto(d.get("cidade"),"cidade",1,80), texto(d.get("uf"),"UF",2,2).upper(), uid)
    except (ValueError, KeyError) as exc:
        raise ErroNegocio(str(exc))
    cur = conexao().cursor()
    cur.execute("INSERT INTO clientes (nome,cpf,telefone,email,cep,logradouro,numero,complemento,bairro,cidade,uf,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", valores)
    cid = cur.lastrowid
    conexao().commit()
    cur.close()
    return cid

def criar_veiculo(d, uid):
    try:
        placa_v = placa(d.get("placa"))
        cliente_id = int(d.get("cliente_id"))
        tipo_id = int(d.get("tipo_veiculo_id"))
        modelo_id = int(d["modelo_id"]) if d.get("modelo_id") else None
        cor_id = int(d["cor_id"]) if d.get("cor_id") else None
    except (ValueError, TypeError) as exc:
        raise ErroNegocio(str(exc) or "Dados do veículo inválidos.")
    cur = conexao().cursor()
    cur.execute("INSERT INTO veiculos (cliente_id,tipo_veiculo_id,placa,modelo_id,cor_id,criado_por) VALUES (%s,%s,%s,%s,%s,%s)", (cliente_id,tipo_id,placa_v,modelo_id,cor_id,uid))
    vid = cur.lastrowid
    conexao().commit()
    cur.close()
    return vid


def _buscar_plano(cur, plano_id):
    cur.execute("SELECT id, nome, cobranca, ativo FROM planos WHERE id = %s", (plano_id,))
    plano = cur.fetchone()
    if not plano:
        raise ErroNegocio("Plano não encontrado.", 404)
    return plano

def criar_plano(d, uid):
    try:
        nome = texto(d.get("nome"), "nome", 1, 30)
        cobranca = d.get("cobranca")
        if cobranca not in ("mensal", "hora"):
            raise ValueError("A cobrança deve ser 'mensal' ou 'hora'.")
    except (ValueError, TypeError) as exc:
        raise ErroNegocio(str(exc))
    conn = conexao()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO planos (nome, cobranca, criado_por) VALUES (%s,%s,%s)", (nome, cobranca, uid))
        pid = cur.lastrowid
        registrar_auditoria("planos", pid, "criou", uid, None, {"nome": nome, "cobranca": cobranca, "ativo": 1})
        conn.commit()
    except IntegrityError:
        conn.rollback()
        raise ErroNegocio("Já existe um plano com esse nome.", 409)
    finally:
        cur.close()
    return pid

def editar_plano(plano_id, d, uid):
    if "cobranca" in d:
        raise ErroNegocio("O tipo de cobrança não pode ser alterado. Crie um novo plano e desative o antigo.")
    try:
        nome = texto(d.get("nome"), "nome", 1, 30)
    except (ValueError, TypeError) as exc:
        raise ErroNegocio(str(exc))
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    try:
        antes = _buscar_plano(cur, plano_id)
        cur.execute("UPDATE planos SET nome = %s, atualizado_por = %s WHERE id = %s", (nome, uid, plano_id))
        registrar_auditoria("planos", plano_id, "alterou", uid, antes, {**antes, "nome": nome})
        conn.commit()
    except IntegrityError:
        conn.rollback()
        raise ErroNegocio("Já existe um plano com esse nome.", 409)
    finally:
        cur.close()

def alterar_situacao_plano(plano_id, ativo, uid):
    ativo = 1 if ativo else 0
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    try:
        antes = _buscar_plano(cur, plano_id)
        cur.execute("UPDATE planos SET ativo = %s, atualizado_por = %s WHERE id = %s", (ativo, uid, plano_id))
        registrar_auditoria("planos", plano_id, "alterou", uid, antes, {**antes, "ativo": ativo})
        conn.commit()
    finally:
        cur.close()


def _valor(v, nome, obrigatorio=True):
    if v in (None, ""):
        if obrigatorio:
            raise ValueError(f"Informe o {nome}.")
        return None
    try:
        d = Decimal(str(v).replace(",", "."))
    except Exception:
        raise ValueError(f"O {nome} é inválido.")
    if not d.is_finite() or d <= 0 or d > Decimal("99999999.99"):
        raise ValueError(f"O {nome} deve ser maior que zero.")
    return d.quantize(Decimal("0.01"))

def listar_precos():
    return _todos(
        "SELECT p.id, p.plano_id, pl.nome AS plano, p.tipo_veiculo_id, t.nome AS tipo_veiculo, p.valor, p.valor_diaria "
        "FROM precos p JOIN planos pl ON pl.id = p.plano_id JOIN tipos_veiculo t ON t.id = p.tipo_veiculo_id "
        "ORDER BY pl.nome, t.nome"
    )

def criar_preco(d, uid):
    for campo in ("plano_id", "tipo_veiculo_id"):
        if not str(d.get(campo) or "").isdigit():
            raise ErroNegocio("Informe o plano e o tipo de veículo.")
    plano_id = int(d["plano_id"])
    tipo_id = int(d["tipo_veiculo_id"])
    try:
        valor = _valor(d.get("valor"), "valor")
        diaria = _valor(d.get("valor_diaria"), "valor da diária", False)
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    try:
        _buscar_plano(cur, plano_id)
        cur.execute("SELECT id FROM tipos_veiculo WHERE id = %s", (tipo_id,))
        if not cur.fetchone():
            raise ErroNegocio("Tipo de veículo não encontrado.", 404)
        cur.execute("SELECT id FROM precos WHERE plano_id = %s AND tipo_veiculo_id = %s", (plano_id, tipo_id))
        if cur.fetchone():
            raise ErroNegocio("Já existe um preço para esse plano e tipo de veículo. Edite o existente.", 409)
        cur.execute(
            "INSERT INTO precos (plano_id, tipo_veiculo_id, valor, valor_diaria, criado_por) VALUES (%s,%s,%s,%s,%s)",
            (plano_id, tipo_id, valor, diaria, uid),
        )
        preco_id = cur.lastrowid
        registrar_auditoria("precos", preco_id, "criou", uid, None,
                            {"plano_id": plano_id, "tipo_veiculo_id": tipo_id, "valor": valor, "valor_diaria": diaria})
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    return preco_id

def editar_preco(preco_id, d, uid):
    try:
        valor = _valor(d.get("valor"), "valor")
        diaria = _valor(d.get("valor_diaria"), "valor da diária", False)
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, valor, valor_diaria FROM precos WHERE id = %s", (preco_id,))
        antes = cur.fetchone()
        if not antes:
            raise ErroNegocio("Preço não encontrado.", 404)
        cur.execute("UPDATE precos SET valor = %s, valor_diaria = %s, atualizado_por = %s WHERE id = %s",
                    (valor, diaria, uid, preco_id))
        registrar_auditoria("precos", preco_id, "alterou", uid, antes, {**antes, "valor": valor, "valor_diaria": diaria})
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

def criar_vaga(d, uid):
    try:
        numero = int(d.get("numero"))
        tipo_id = int(d.get("tipo_veiculo_id"))
        plano_id = int(d.get("plano_id"))
    except (ValueError, TypeError):
        raise ErroNegocio("Informe número, tipo de veículo e plano da vaga.")
    if not 1 <= numero <= 9999:
        raise ErroNegocio("O número da vaga deve estar entre 1 e 9999.")
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM tipos_veiculo WHERE id = %s", (tipo_id,))
        if not cur.fetchone():
            raise ErroNegocio("Tipo de veículo não encontrado.", 404)
        plano = _buscar_plano(cur, plano_id)
        if not plano["ativo"]:
            raise ErroNegocio("Não é possível criar vaga em um plano inativo.")
        cur.execute("SELECT id FROM vagas WHERE numero = %s", (numero,))
        if cur.fetchone():
            raise ErroNegocio("Já existe uma vaga com esse número.", 409)
        cur.execute("INSERT INTO vagas (numero, tipo_veiculo_id, plano_id, ativo, criado_por) VALUES (%s,%s,%s,1,%s)", (numero, tipo_id, plano_id, uid))
        vid = cur.lastrowid
        registrar_auditoria("vagas", vid, "criou", uid, None, {"numero": numero, "tipo_veiculo_id": tipo_id, "plano_id": plano_id, "ativo": 1})
        conn.commit()
    except IntegrityError:
        conn.rollback()
        raise ErroNegocio("Já existe uma vaga com esse número.", 409)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    return vid


CATALOGOS_EDITAVEIS = {"cores", "tipos_veiculo", "marcas", "modelos"}

def criar_item_catalogo(tabela, d, uid):
    if tabela not in CATALOGOS_EDITAVEIS:
        raise ErroNegocio("Catálogo inválido.")

    try:
        nome = texto(d.get("nome"), "nome", 1, 60)
    except (ValueError, TypeError) as exc:
        raise ErroNegocio(str(exc))

    conn = conexao()
    cur = conn.cursor(dictionary=True)
    try:
        # Descobre as colunas existentes para manter compatibilidade com versões
        # diferentes do esquema do banco.
        cur.execute(f"SHOW COLUMNS FROM {tabela}")
        definicoes = {r["Field"]: r for r in cur.fetchall()}
        colunas = set(definicoes)
        campos = {"nome": nome}
        filtros = ["LOWER(nome) = LOWER(%s)"]
        params = [nome]
        auditoria = {"nome": nome}

        if tabela == "modelos":
            # O banco atual exige tipo_veiculo_id para cada modelo.
            if "tipo_veiculo_id" in colunas:
                valor_tipo = d.get("tipo_veiculo_id")
                if not str(valor_tipo or "").isdigit():
                    raise ErroNegocio("Escolha o tipo de veículo do modelo.")
                tipo_id = int(valor_tipo)
                cur.execute("SELECT id FROM tipos_veiculo WHERE id = %s", (tipo_id,))
                if not cur.fetchone():
                    raise ErroNegocio("Tipo de veículo não encontrado.", 404)
                campos["tipo_veiculo_id"] = tipo_id
                auditoria["tipo_veiculo_id"] = tipo_id
                filtros.append("tipo_veiculo_id = %s")
                params.append(tipo_id)

            if "marca_id" in colunas:
                valor_marca = d.get("marca_id")
                if not str(valor_marca or "").isdigit():
                    raise ErroNegocio("Escolha a marca do modelo.")
                marca_id = int(valor_marca)
                cur.execute("SELECT id FROM marcas WHERE id = %s", (marca_id,))
                if not cur.fetchone():
                    raise ErroNegocio("Marca não encontrada.", 404)
                campos["marca_id"] = marca_id
                auditoria["marca_id"] = marca_id
                filtros.append("marca_id = %s")
                params.append(marca_id)

        cur.execute(f"SELECT id FROM {tabela} WHERE {' AND '.join(filtros)}", params)
        if cur.fetchone():
            raise ErroNegocio("Já existe um registro com esses dados.", 409)

        if "criado_por" in colunas:
            campos["criado_por"] = uid
        if "ativo" in colunas:
            campos["ativo"] = 1

        nomes = ", ".join(campos)
        marcadores = ", ".join(["%s"] * len(campos))
        cur.execute(
            f"INSERT INTO {tabela} ({nomes}) VALUES ({marcadores})",
            list(campos.values()),
        )
        novo_id = cur.lastrowid
        registrar_auditoria(tabela, novo_id, "criou", uid, None, auditoria)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    return novo_id
