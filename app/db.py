import time
from contextlib import contextmanager
from mysql.connector.errors import PoolError
from mysql.connector.pooling import MySQLConnectionPool
from flask import current_app, g

_pool = None

def inicializar_pool(app):
    global _pool
    cfg = app.config
    _pool = MySQLConnectionPool(
        pool_name="estacionamento_pool",
        pool_size=max(1, min(cfg["DB_POOL_SIZE"], 32)),
        host=cfg["DB_HOST"], port=cfg["DB_PORT"], database=cfg["DB_NAME"],
        user=cfg["DB_USER"], password=cfg["DB_PASSWORD"],
        charset="utf8mb4", collation="utf8mb4_unicode_ci", autocommit=False,
    )

def conexao():
    if "db_connection" not in g:
        if _pool is None:
            inicializar_pool(current_app)
        # Se todas as conexões estiverem em uso, espera até ~5 s por uma livre em vez de falhar na hora.
        for tentativa in range(50):
            try:
                g.db_connection = _pool.get_connection()
                break
            except PoolError:
                if tentativa == 49:
                    raise
                time.sleep(0.1)
    return g.db_connection

@contextmanager
def transacao():
    conn = conexao()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def fechar_conexao(_erro=None):
    conn = g.pop("db_connection", None)
    if conn is not None:
        if conn.is_connected():
            try:
                conn.rollback()
            except Exception:
                pass
            conn.close()
