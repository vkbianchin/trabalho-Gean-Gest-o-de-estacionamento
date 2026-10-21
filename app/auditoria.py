import json
from .db import conexao

CAMPOS_SENSIVEIS = {"senha", "senha_hash", "password", "token", "preferencias"}

def _limpar(dados):
    if not isinstance(dados, dict):
        return dados
    return {k: v for k, v in dados.items() if k.lower() not in CAMPOS_SENSIVEIS}

def registrar(tabela, registro_id, acao, usuario_id, antes=None, depois=None):
    antes = _limpar(antes)
    depois = _limpar(depois)
    if antes is not None and depois is not None:
        antes_filtrado = {}
        depois_filtrado = {}
        for chave in set(antes) | set(depois):
            if antes.get(chave) != depois.get(chave):
                antes_filtrado[chave] = antes.get(chave)
                depois_filtrado[chave] = depois.get(chave)
        antes, depois = antes_filtrado, depois_filtrado
        if not antes:
            return
    conn = conexao()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO auditoria (tabela, registro_id, acao, usuario_id, dados_antes, dados_depois) VALUES (%s,%s,%s,%s,%s,%s)",
        (tabela, int(registro_id), acao, int(usuario_id), json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
         json.dumps(depois, ensure_ascii=False, default=str) if depois is not None else None),
    )
    cur.close()
