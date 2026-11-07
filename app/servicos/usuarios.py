import json
import secrets
import time
from datetime import timedelta
from math import ceil
from mysql.connector.errors import Error as ErroMySQL
from flask import session, current_app
from ..db import conexao, transacao
from ..seguranca import gerar_hash, verificar_hash
from ..erros import ErroNegocio
from ..tempo import agora
from ..validadores import senha as validar_senha, texto, email
from ..auditoria import registrar as registrar_auditoria
from .. import totp

# Política de limitação de tentativas de login:
# 5 falhas seguidas bloqueiam a conta por 15 minutos; depois o bloqueio expira sozinho.
# A contagem fica no banco (usuarios.tentativas_login e usuarios.bloqueado_ate).
MAX_TENTATIVAS = 5
BLOQUEIO_MINUTOS = 15

# Logins que não existem também são limitados (só em memória), para que o bloqueio
# não revele quais logins existem no sistema.
_LIMITE_DESCONHECIDOS = 5000
_desconhecidos = {}

def bloqueado(bloqueado_ate, referencia):
    return bool(bloqueado_ate) and bloqueado_ate > referencia

def minutos_restantes(bloqueado_ate, referencia):
    return max(1, ceil((bloqueado_ate - referencia).total_seconds() / 60))

def _erro_bloqueio(bloqueado_ate=None, referencia=None):
    if bloqueado_ate and referencia:
        return ErroNegocio(f"Muitas tentativas. Tente novamente em {minutos_restantes(bloqueado_ate, referencia)} minuto(s).", 429)
    return ErroNegocio("Muitas tentativas. Aguarde alguns minutos e tente novamente.", 429)

def _desconhecido_bloqueado(chave, referencia):
    registro = _desconhecidos.get(chave)
    return registro["ate"] if registro and bloqueado(registro["ate"], referencia) else None

def _desconhecido_falhou(chave, referencia):
    """Conta a falha de um login inexistente; devolve o fim do bloqueio se ele foi acionado agora."""
    if len(_desconhecidos) >= _LIMITE_DESCONHECIDOS:
        _desconhecidos.clear()
    registro = _desconhecidos.setdefault(chave, {"falhas": 0, "ate": None})
    registro["falhas"] += 1
    if registro["falhas"] >= MAX_TENTATIVAS:
        registro["falhas"] = 0
        registro["ate"] = referencia + timedelta(minutes=BLOQUEIO_MINUTOS)
        return registro["ate"]
    return None

# "atualizado_em = atualizado_em" evita que o contador de login altere a data de atualização do usuário.
def _reservar_tentativa(uid):
    """Conta a tentativa ANTES de conferir a senha (operação atômica no banco), para que
    várias tentativas simultâneas não ultrapassem o limite."""
    conn = conexao()
    with transacao():
        cur = conn.cursor(dictionary=True)
        cur.execute("UPDATE usuarios SET tentativas_login = tentativas_login + 1, atualizado_em = atualizado_em WHERE id=%s", (uid,))
        cur.execute("SELECT tentativas_login FROM usuarios WHERE id=%s FOR UPDATE", (uid,))
        tentativas = int(cur.fetchone()["tentativas_login"])
        cur.close()
    return tentativas

def _bloquear(uid, ate):
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=%s, atualizado_em = atualizado_em WHERE id=%s", (ate, uid))
        cur.close()

def _zerar_tentativas(uid):
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET tentativas_login=0, bloqueado_ate=NULL, atualizado_em = atualizado_em WHERE id=%s", (uid,))
        cur.close()

def login(login, senha):
    chave = (login or "").strip().lower()[:150]
    referencia = agora()
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT id, nome, login, senha_hash, nivel_acesso, trocar_senha, ativo, bloqueado_ate FROM usuarios WHERE login=%s OR email=%s LIMIT 1", (chave, chave))
    usuario = cur.fetchone()
    cur.close()
    if not usuario:
        ate = _desconhecido_bloqueado(chave, referencia) or _desconhecido_falhou(chave, referencia)
        if ate:
            raise _erro_bloqueio(ate, referencia)
        raise ErroNegocio("Login ou senha incorretos.", 401)
    if bloqueado(usuario["bloqueado_ate"], referencia):
        raise _erro_bloqueio(usuario["bloqueado_ate"], referencia)
    tentativas = _reservar_tentativa(usuario["id"])
    if tentativas > MAX_TENTATIVAS:
        raise _erro_bloqueio()
    if not usuario["ativo"] or not verificar_hash(senha or "", usuario["senha_hash"]):
        if tentativas >= MAX_TENTATIVAS:
            ate = referencia + timedelta(minutes=BLOQUEIO_MINUTOS)
            _bloquear(usuario["id"], ate)
            current_app.logger.warning("Login bloqueado por excesso de tentativas: usuario_id=%s", usuario["id"])
            raise _erro_bloqueio(ate, referencia)
        raise ErroNegocio("Login ou senha incorretos.", 401)
    _zerar_tentativas(usuario["id"])
    _desconhecidos.pop(chave, None)
    if _ler_coluna(usuario["id"], "totp_ativo"):
        # Senha correta, mas falta o código do aplicativo autenticador: a sessão só é aberta depois dele.
        session.clear()
        session["pre2fa"] = {"uid": usuario["id"], "expira": time.time() + PRAZO_2FA_SEGUNDOS}
        return {"exige_2fa": True}
    return _iniciar_sessao(usuario)


PRAZO_2FA_SEGUNDOS = 300


def _ler_coluna(uid, coluna):
    """Lê uma coluna criada por migração opcional (005 preferências, 006 2FA). Sem a migração, devolve None."""
    cur = conexao().cursor(dictionary=True)
    try:
        cur.execute(f"SELECT {coluna} AS valor FROM usuarios WHERE id=%s", (uid,))
        linha = cur.fetchone()
        return linha["valor"] if linha else None
    except ErroMySQL as exc:
        if getattr(exc, "errno", None) == 1054:  # coluna desconhecida
            return None
        raise
    finally:
        cur.close()


def _iniciar_sessao(usuario):
    preferencias = _ler_coluna(usuario["id"], "preferencias")
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario["id"]
    session["nome"] = usuario["nome"]
    session["login"] = usuario["login"]
    session["nivel_acesso"] = usuario["nivel_acesso"]
    session["trocar_senha"] = bool(usuario["trocar_senha"])
    session["permitir_troca_senha"] = False
    if preferencias:
        try:
            session["preferencias"] = json.loads(preferencias) if isinstance(preferencias, (str, bytes, bytearray)) else dict(preferencias)
        except (ValueError, TypeError):
            pass
    return {k: usuario[k] for k in ("id", "nome", "login", "nivel_acesso", "trocar_senha")}


def login_segundo_fator(codigo):
    """Segunda etapa do login: confere o código do aplicativo autenticador."""
    pendente = session.get("pre2fa")
    if not pendente or time.time() > pendente["expira"]:
        session.pop("pre2fa", None)
        raise ErroNegocio("A verificação expirou. Entre novamente com login e senha.", 401)
    referencia = agora()
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT id, nome, login, nivel_acesso, trocar_senha, ativo, bloqueado_ate FROM usuarios WHERE id=%s", (pendente["uid"],))
    usuario = cur.fetchone()
    cur.close()
    if not usuario or not usuario["ativo"]:
        session.clear()
        raise ErroNegocio("Login ou senha incorretos.", 401)
    if bloqueado(usuario["bloqueado_ate"], referencia):
        raise _erro_bloqueio(usuario["bloqueado_ate"], referencia)
    tentativas = _reservar_tentativa(usuario["id"])
    segredo = _ler_coluna(usuario["id"], "totp_segredo")
    if tentativas > MAX_TENTATIVAS or not segredo or not totp.verificar(segredo, codigo):
        if tentativas >= MAX_TENTATIVAS:
            ate = referencia + timedelta(minutes=BLOQUEIO_MINUTOS)
            _bloquear(usuario["id"], ate)
            session.clear()
            current_app.logger.warning("Segundo fator bloqueado por excesso de tentativas: usuario_id=%s", usuario["id"])
            raise _erro_bloqueio(ate, referencia)
        raise ErroNegocio("Código inválido ou expirado.", 401)
    _zerar_tentativas(usuario["id"])
    return _iniciar_sessao(usuario)


def trocar_senha(usuario_id, atual, nova):
    validar_senha(nova)
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT senha_hash FROM usuarios WHERE id=%s AND ativo=1", (usuario_id,))
    usuario = cur.fetchone()
    cur.close()
    if not usuario or not verificar_hash(atual or "", usuario["senha_hash"]):
        raise ErroNegocio("A senha atual está incorreta.", 400)
    conn = conexao()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET senha_hash=%s, trocar_senha=0, atualizado_por=%s WHERE id=%s", (gerar_hash(nova), usuario_id, usuario_id))
    cur.close()
    conn.commit()
    session["trocar_senha"] = False
    session["permitir_troca_senha"] = False

def criar_usuario(nome, email_usuario, login_usuario, senha_inicial, nivel, criador_id, provisoria=False):
    try:
        nome = texto(nome, "nome", 2, 100)
        email_usuario = email(email_usuario, True)
        login_usuario = texto(login_usuario, "login", 3, 50).lower()
    except ValueError as exc:
        raise ErroNegocio(str(exc))
    if nivel not in ("administrador", "operador"):
        raise ErroNegocio("Nível de acesso inválido.")
    hash_senha = gerar_hash(senha_inicial)
    conn = conexao()
    cur = conn.cursor()
    cur.execute("INSERT INTO usuarios (nome,email,login,senha_hash,nivel_acesso,trocar_senha,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s)", (nome,email_usuario,login_usuario,hash_senha,nivel,int(provisoria),criador_id))
    uid = cur.lastrowid
    if criador_id:  # o primeiro administrador, criado por script, não tem quem registrar como autor
        registrar_auditoria("usuarios", uid, "criou", criador_id, None, {"nome": nome, "email": email_usuario, "login": login_usuario, "nivel_acesso": nivel})
    conn.commit()
    cur.close()
    return uid


# ---------------------------------------------------------------- autenticação em dois fatores (migração 006)
def status_2fa(uid):
    return {"ativo": bool(_ler_coluna(uid, "totp_ativo"))}


def iniciar_2fa(uid, conta):
    """Gera um segredo novo. Ele só vale depois de confirmado com um código (confirmar_2fa)."""
    if _ler_coluna(uid, "totp_ativo"):
        raise ErroNegocio("A verificação em duas etapas já está ativa.")
    segredo = totp.gerar_segredo()
    session["totp_pendente"] = segredo
    return {"segredo": segredo, "uri": totp.uri_provisionamento(segredo, conta)}


def confirmar_2fa(uid, codigo):
    segredo = session.get("totp_pendente")
    if not segredo:
        raise ErroNegocio("Inicie a configuração antes de confirmar o código.")
    if not totp.verificar(segredo, codigo):
        raise ErroNegocio("Código inválido. Confira a hora do celular e tente de novo.")
    conn = conexao()
    try:
        with transacao():
            cur = conn.cursor()
            cur.execute("UPDATE usuarios SET totp_segredo=%s, totp_ativo=1, atualizado_por=%s WHERE id=%s", (segredo, uid, uid))
            cur.close()
            registrar_auditoria("usuarios", uid, "ativou 2fa", uid, {"totp_ativo": 0}, {"totp_ativo": 1})
    except ErroMySQL as exc:
        if getattr(exc, "errno", None) == 1054:
            raise ErroNegocio("Aplique a migração 006 do banco para usar a verificação em duas etapas.")
        raise
    session.pop("totp_pendente", None)
    return {"mensagem": "Verificação em duas etapas ativada."}


def desativar_2fa(uid, senha, codigo):
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT senha_hash FROM usuarios WHERE id=%s AND ativo=1", (uid,))
    usuario = cur.fetchone()
    cur.close()
    segredo = _ler_coluna(uid, "totp_segredo")
    if not usuario or not verificar_hash(senha or "", usuario["senha_hash"]):
        raise ErroNegocio("Senha incorreta.", 400)
    if not segredo or not totp.verificar(segredo, codigo):
        raise ErroNegocio("Código inválido ou expirado.", 400)
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET totp_segredo=NULL, totp_ativo=0, atualizado_por=%s WHERE id=%s", (uid, uid))
        cur.close()
        registrar_auditoria("usuarios", uid, "desativou 2fa", uid, {"totp_ativo": 1}, {"totp_ativo": 0})
    return {"mensagem": "Verificação em duas etapas desativada."}


# ---------------------------------------------------------------- administração de usuários
def gerar_senha_temporaria(tamanho=12):
    """Senha provisória legível (sem 0/O/1/l/I) que sempre cumpre a política: letras e números."""
    letras = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    numeros = "23456789"
    while True:
        senha = "".join(secrets.choice(letras + numeros) for _ in range(tamanho))
        if any(c in letras for c in senha) and any(c in numeros for c in senha):
            return senha


def redefinir_senha_admin(alvo_id, admin_id):
    """O administrador gera uma senha provisória para outro usuário (que terá de trocá-la no próximo acesso)."""
    if alvo_id == admin_id:
        raise ErroNegocio("Para trocar a própria senha use a opção Trocar senha.")
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT id, ativo FROM usuarios WHERE id=%s", (alvo_id,))
    alvo = cur.fetchone()
    cur.close()
    if not alvo:
        raise ErroNegocio("Usuário não encontrado.", 404)
    senha = gerar_senha_temporaria()
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET senha_hash=%s, trocar_senha=1, tentativas_login=0, bloqueado_ate=NULL, atualizado_por=%s WHERE id=%s", (gerar_hash(senha), admin_id, alvo_id))
        cur.close()
        registrar_auditoria("usuarios", alvo_id, "redefiniu senha", admin_id, None, {"trocar_senha": 1})
    return {"senha_provisoria": senha, "mensagem": "Senha redefinida. Informe a senha provisória ao usuário; ela aparece só desta vez."}


def reativar_usuario(alvo_id, admin_id):
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT ativo FROM usuarios WHERE id=%s", (alvo_id,))
    alvo = cur.fetchone()
    cur.close()
    if not alvo:
        raise ErroNegocio("Usuário não encontrado.", 404)
    if alvo["ativo"]:
        return {"mensagem": "O usuário já está ativo."}
    conn = conexao()
    with transacao():
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET ativo=1, tentativas_login=0, bloqueado_ate=NULL, atualizado_por=%s WHERE id=%s", (admin_id, alvo_id))
        cur.close()
        registrar_auditoria("usuarios", alvo_id, "reativou", admin_id, {"ativo": 0}, {"ativo": 1})
    return {"mensagem": "Usuário reativado."}


def salvar_preferencias(uid, preferencias):
    """Guarda as preferências de aparência no banco (coluna da migração 005); sem ela, valem só na sessão."""
    session["preferencias"] = preferencias
    conn = conexao()
    try:
        with transacao():
            cur = conn.cursor()
            cur.execute("UPDATE usuarios SET preferencias=%s WHERE id=%s", (json.dumps(preferencias), uid))
            cur.close()
        return True
    except ErroMySQL as exc:
        if getattr(exc, "errno", None) == 1054:
            return False
        raise
