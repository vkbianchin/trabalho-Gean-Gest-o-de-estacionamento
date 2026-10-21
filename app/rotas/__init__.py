from .acesso import bp as acesso_bp
from .cadastros import bp as cadastros_bp
from .vagas import bp as vagas_bp
from .contratos import bp as contratos_bp
from .movimentacoes import bp as movimentacoes_bp
from .pagamentos import bp as pagamentos_bp
from .caixa import bp as caixa_bp
from .sistema import bp as sistema_bp
from .paginas import bp as paginas_bp
from .administracao import bp as administracao_bp

def registrar_rotas(app):
    for bp in (acesso_bp,cadastros_bp,vagas_bp,contratos_bp,movimentacoes_bp,pagamentos_bp,caixa_bp,sistema_bp,paginas_bp,administracao_bp):
        app.register_blueprint(bp)
