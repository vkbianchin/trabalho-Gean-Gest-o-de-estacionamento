from app import create_app
from app.db import conexao
from app.servicos.sistema import dados_iniciais

app=create_app()
with app.app_context():
    cur=conexao().cursor(dictionary=True)
    cur.execute("SELECT id FROM usuarios WHERE ativo=1 ORDER BY id LIMIT 1")
    usuario=cur.fetchone(); cur.close()
    if not usuario: raise SystemExit("Crie o primeiro administrador antes de inserir dados iniciais.")
    dados_iniciais(usuario["id"])
    print("Dados iniciais conferidos/inseridos: planos, tipos de veículo, cores e configurações.")
