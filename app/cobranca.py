from decimal import Decimal, ROUND_CEILING

def calcular_cobranca(entrada, saida, valor_hora, tolerancia_minutos=10, arredondamento="fracao", fracao_minutos=30, valor_diaria=None):
    """Calcula preço usando Decimal. Datas devem ser datetime sem fuso, ambas no horário local de Brasília."""
    if saida < entrada:
        raise ValueError("A saída não pode ser anterior à entrada.")
    minutos = int((saida - entrada).total_seconds() // 60)
    excedente = minutos - int(tolerancia_minutos)
    if excedente <= 0:
        return Decimal("0.00")
    hora = Decimal(str(valor_hora))
    if hora < 0:
        raise ValueError("O valor por hora não pode ser negativo.")
    if arredondamento == "hora_cheia":
        unidade = 60
    elif arredondamento == "fracao":
        unidade = int(fracao_minutos)
        if not 1 <= unidade <= 60:
            raise ValueError("A fração deve estar entre 1 e 60 minutos.")
    else:
        raise ValueError("Regra de arredondamento inválida.")
    if valor_diaria is not None:
        diaria = Decimal(str(valor_diaria))
        if diaria < 0:
            raise ValueError("A diária não pode ser negativa.")
        blocos, resto = divmod(excedente, 1440)
        valor = diaria * blocos
        if resto:
            unidades = (Decimal(resto) / Decimal(unidade)).to_integral_value(rounding=ROUND_CEILING)
            parcial = hora * Decimal(unidade) / Decimal(60) * unidades
            valor += min(parcial, diaria)
    else:
        unidades = (Decimal(excedente) / Decimal(unidade)).to_integral_value(rounding=ROUND_CEILING)
        valor = hora * Decimal(unidade) / Decimal(60) * unidades
    return valor.quantize(Decimal("0.01"))
