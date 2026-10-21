from app.permissoes import PERMISSOES

def test_operador_nao_tem_permissao_administrativa():
    assert "operador" not in PERMISSOES["contratos"]
    assert "operador" not in PERMISSOES["usuarios"]
    assert "operador" in PERMISSOES["operacao"]
