"""Edição e ativação/desativação de clientes, veículos e vagas, com travas para não quebrar contratos nem vagas em uso."""
from mysql.connector.errors import IntegrityError

from ..auditoria import registrar as registrar_auditoria
from ..db import conexao, transacao
from ..erros import ErroNegocio
from . import cadastros


def _linha(sql, params=()):
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()


def _existe(sql, params=()):
    return _linha(sql, params) is not None


def _atualizar(tabela, ident, valores):
    """UPDATE de colunas escolhidas pelo código (nunca por texto vindo do usuário)."""
    cur = conexao().cursor()
    try:
        cur.execute(f"UPDATE {tabela} SET " + ", ".join(f"{c}=%s" for c in valores) + " WHERE id=%s", [*valores.values(), ident])
    finally:
        cur.close()


def _diferencas(antes, novos):
    return {k: v for k, v in novos.items() if antes.get(k) != v}


# ---------------------------------------------------------------- clientes
def obter_cliente(cid):
    c = _linha("SELECT id,nome,tipo_pessoa,documento,telefone,email,cep,logradouro,numero,complemento,bairro,cidade,uf,ativo FROM clientes WHERE id=%s", (cid,))
    if not c:
        raise ErroNegocio("Cliente não encontrado.", 404)
    return c


def editar_cliente(cid, d, uid):
    antes = obter_cliente(cid)
    try:
        novos = cadastros.dados_cadastrais(d, antes["tipo_pessoa"])
    except (ValueError, KeyError) as exc:
        raise ErroNegocio(str(exc))
    mudou = _diferencas(antes, novos)
    if not mudou:
        return {"mensagem": "Nenhuma alteração a salvar."}
    with transacao():
        _atualizar("clientes", cid, mudou)
        registrar_auditoria("clientes", cid, "alterou", uid, {k: antes[k] for k in mudou}, mudou)
    return {"mensagem": "Cliente atualizado."}


def alterar_situacao_cliente(cid, ativo, uid):
    cliente = obter_cliente(cid)
    ativo = 1 if ativo else 0
    if cliente["ativo"] == ativo:
        return {"mensagem": "O cliente já está nessa situação."}
    if not ativo and _existe("SELECT id FROM contratos_mensalistas WHERE cliente_id=%s AND data_fim IS NULL", (cid,)):
        raise ErroNegocio("Este cliente tem contrato mensalista vigente. Encerre o contrato antes de desativar.")
    with transacao():
        _atualizar("clientes", cid, {"ativo": ativo})
        registrar_auditoria("clientes", cid, "ativou" if ativo else "desativou", uid, {"ativo": cliente["ativo"]}, {"ativo": ativo})
    return {"mensagem": "Cliente ativado." if ativo else "Cliente desativado."}


# ---------------------------------------------------------------- veículos
def obter_veiculo(vid):
    v = _linha("SELECT v.id,v.placa,v.cliente_id,v.tipo_veiculo_id,v.modelo_id,v.cor_id,v.ativo,c.ativo AS cliente_ativo FROM veiculos v JOIN clientes c ON c.id=v.cliente_id WHERE v.id=%s", (vid,))
    if not v:
        raise ErroNegocio("Veículo não encontrado.", 404)
    return v


def _id_opcional(valor, nome):
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ErroNegocio(f"{nome} inválido.")


def editar_veiculo(vid, d, uid):
    """Altera modelo e cor. A placa, o dono e o tipo não mudam (um veículo diferente deve ser um novo cadastro)."""
    antes = obter_veiculo(vid)
    novos = {"modelo_id": _id_opcional(d.get("modelo_id"), "Modelo"), "cor_id": _id_opcional(d.get("cor_id"), "Cor")}
    if novos["modelo_id"] is not None:
        modelo = _linha("SELECT tipo_veiculo_id FROM modelos WHERE id=%s", (novos["modelo_id"],))
        if not modelo:
            raise ErroNegocio("Modelo não encontrado.", 404)
        if modelo["tipo_veiculo_id"] != antes["tipo_veiculo_id"]:
            raise ErroNegocio("O modelo escolhido não é compatível com o tipo deste veículo.")
    if novos["cor_id"] is not None and not _existe("SELECT id FROM cores WHERE id=%s", (novos["cor_id"],)):
        raise ErroNegocio("Cor não encontrada.", 404)
    mudou = _diferencas(antes, novos)
    if not mudou:
        return {"mensagem": "Nenhuma alteração a salvar."}
    with transacao():
        _atualizar("veiculos", vid, mudou)
        registrar_auditoria("veiculos", vid, "alterou", uid, {k: antes[k] for k in mudou}, mudou)
    return {"mensagem": "Veículo atualizado."}


def alterar_situacao_veiculo(vid, ativo, uid):
    veiculo = obter_veiculo(vid)
    ativo = 1 if ativo else 0
    if veiculo["ativo"] == ativo:
        return {"mensagem": "O veículo já está nessa situação."}
    if ativo and not veiculo["cliente_ativo"]:
        raise ErroNegocio("O cliente deste veículo está inativo. Ative o cliente primeiro.")
    if not ativo:
        if _existe("SELECT id FROM contratos_mensalistas WHERE veiculo_id=%s AND data_fim IS NULL", (vid,)):
            raise ErroNegocio("Este veículo tem contrato mensalista vigente. Encerre o contrato antes de desativar.")
        if _existe("SELECT id FROM movimentacoes WHERE placa=%s AND saida_em IS NULL AND cancelada=0", (veiculo["placa"],)):
            raise ErroNegocio("Este veículo está estacionado agora. Registre a saída antes de desativar.")
    with transacao():
        _atualizar("veiculos", vid, {"ativo": ativo})
        registrar_auditoria("veiculos", vid, "ativou" if ativo else "desativou", uid, {"ativo": veiculo["ativo"]}, {"ativo": ativo})
    return {"mensagem": "Veículo ativado." if ativo else "Veículo desativado."}


# ---------------------------------------------------------------- vagas
def obter_vaga(vid):
    v = _linha("SELECT g.id,g.numero,g.tipo_veiculo_id,g.plano_id,g.ativo,p.cobranca,p.ativo AS plano_ativo FROM vagas g JOIN planos p ON p.id=g.plano_id WHERE g.id=%s", (vid,))
    if not v:
        raise ErroNegocio("Vaga não encontrada.", 404)
    return v


def _vaga_ocupada(vid):
    return _existe("SELECT id FROM movimentacoes WHERE vaga_id=%s AND saida_em IS NULL AND cancelada=0", (vid,))


def _garantir_vagas_mensais(vaga):
    """Retirar uma vaga mensal não pode deixar contratos vigentes sem vaga (mesma regra usada ao criar contrato)."""
    if vaga["cobranca"] != "mensal" or not vaga["ativo"]:
        return
    tipo = vaga["tipo_veiculo_id"]
    vigentes = _linha("SELECT COUNT(*) AS n FROM contratos_mensalistas c JOIN veiculos v ON v.id=c.veiculo_id WHERE c.data_fim IS NULL AND v.tipo_veiculo_id=%s", (tipo,))["n"]
    restantes = _linha("SELECT COUNT(*) AS n FROM vagas g JOIN planos p ON p.id=g.plano_id WHERE g.ativo=1 AND p.cobranca='mensal' AND g.tipo_veiculo_id=%s AND g.id<>%s", (tipo, vaga["id"]))["n"]
    if vigentes > restantes:
        raise ErroNegocio("Há contratos mensalistas que dependem desta vaga. Encerre um contrato antes de retirá-la.")


def editar_vaga(vid, d, uid):
    antes = obter_vaga(vid)
    try:
        numero = int(d.get("numero", antes["numero"]))
        tipo_id = int(d.get("tipo_veiculo_id", antes["tipo_veiculo_id"]))
        plano_id = int(d.get("plano_id", antes["plano_id"]))
    except (TypeError, ValueError):
        raise ErroNegocio("Informe número, tipo de veículo e plano válidos.")
    if not 1 <= numero <= 9999:
        raise ErroNegocio("O número da vaga deve estar entre 1 e 9999.")
    novos = {"numero": numero, "tipo_veiculo_id": tipo_id, "plano_id": plano_id}
    mudou = _diferencas(antes, novos)
    if not mudou:
        return {"mensagem": "Nenhuma alteração a salvar."}
    if ("tipo_veiculo_id" in mudou or "plano_id" in mudou) and _vaga_ocupada(vid):
        raise ErroNegocio("A vaga está ocupada. Só é possível trocar o tipo ou o plano depois da saída do veículo.")
    if "tipo_veiculo_id" in mudou and not _existe("SELECT id FROM tipos_veiculo WHERE id=%s", (tipo_id,)):
        raise ErroNegocio("Tipo de veículo não encontrado.", 404)
    cobranca_nova = antes["cobranca"]
    if "plano_id" in mudou:
        plano = _linha("SELECT ativo,cobranca FROM planos WHERE id=%s", (plano_id,))
        if not plano:
            raise ErroNegocio("Plano não encontrado.", 404)
        if not plano["ativo"]:
            raise ErroNegocio("Não é possível usar um plano inativo.")
        cobranca_nova = plano["cobranca"]
    continua_mensal = cobranca_nova == "mensal" and tipo_id == antes["tipo_veiculo_id"]
    if antes["ativo"] and not continua_mensal:
        _garantir_vagas_mensais(antes)  # a vaga deixa de ser mensal deste tipo: confere se os contratos ainda cabem
    try:
        with transacao():
            _atualizar("vagas", vid, mudou)
            registrar_auditoria("vagas", vid, "alterou", uid, {k: antes[k] for k in mudou}, mudou)
    except IntegrityError:
        raise ErroNegocio("Já existe uma vaga com esse número.", 409)
    return {"mensagem": "Vaga atualizada."}


def alterar_situacao_vaga(vid, ativo, uid):
    vaga = obter_vaga(vid)
    ativo = 1 if ativo else 0
    if vaga["ativo"] == ativo:
        return {"mensagem": "A vaga já está nessa situação."}
    if ativo and not vaga["plano_ativo"]:
        raise ErroNegocio("O plano desta vaga está inativo. Ative o plano ou troque o plano da vaga.")
    if not ativo:
        if _vaga_ocupada(vid):
            raise ErroNegocio("A vaga está ocupada. Registre a saída antes de desativar.")
        _garantir_vagas_mensais(vaga)
    with transacao():
        _atualizar("vagas", vid, {"ativo": ativo})
        registrar_auditoria("vagas", vid, "ativou" if ativo else "desativou", uid, {"ativo": vaga["ativo"]}, {"ativo": ativo})
    return {"mensagem": "Vaga ativada." if ativo else "Vaga desativada."}
