from ..db import conexao, transacao
from ..erros import ErroNegocio

def dados_iniciais(usuario_id):
    """Idempotente: insere catálogos padrão sem duplicar dados existentes."""
    conn = conexao()
    with transacao() as _:
        cur = conn.cursor()
        for nome, cobranca in (("Mensalista", "mensal"), ("Horista", "hora")):
            cur.execute("INSERT INTO planos (nome,cobranca,criado_por) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE nome=VALUES(nome)", (nome,cobranca,usuario_id))
        for nome in ("Carro", "Moto"):
            cur.execute("INSERT INTO tipos_veiculo (nome,criado_por) VALUES (%s,%s) ON DUPLICATE KEY UPDATE nome=VALUES(nome)", (nome,usuario_id))
        for nome in ("Branco", "Preto", "Prata", "Cinza", "Vermelho", "Azul", "Verde", "Amarelo", "Marrom", "Outra"):
            cur.execute("INSERT INTO cores (nome,criado_por) VALUES (%s,%s) ON DUPLICATE KEY UPDATE nome=VALUES(nome)", (nome,usuario_id))
        cur.execute("INSERT INTO configuracoes (id,tolerancia_minutos,arredondamento,fracao_minutos,nome_estacionamento,criado_por) VALUES (1,10,'fracao',30,'Estacionamento',%s) ON DUPLICATE KEY UPDATE id=id", (usuario_id,))
        cur.close()

def status_sistema():
    conn = conexao()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id,nome_estacionamento,tolerancia_minutos,arredondamento,fracao_minutos FROM configuracoes WHERE id=1")
    config = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS total FROM vagas WHERE ativo=1")
    vagas = cur.fetchone()["total"]
    cur.close()
    return {"configuracoes": config, "vagas_ativas": vagas}
