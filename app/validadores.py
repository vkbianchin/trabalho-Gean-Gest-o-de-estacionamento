import re
from decimal import Decimal, InvalidOperation

_RE_PLACA = re.compile(r"^(?:[A-Z]{3}[0-9][A-Z0-9][0-9]{2})$")
_RE_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def texto(valor, campo, minimo=1, maximo=255):
    if not isinstance(valor, str):
        raise ValueError(f"Informe {campo}.")
    valor = valor.strip()
    if len(valor) < minimo or len(valor) > maximo:
        raise ValueError(f"{campo.capitalize()} deve ter entre {minimo} e {maximo} caracteres.")
    return valor

def placa(valor):
    valor = re.sub(r"[^A-Za-z0-9]", "", str(valor or "")).upper()
    if not _RE_PLACA.fullmatch(valor):
        raise ValueError("Placa inválida. Use o formato ABC1234 ou ABC1D23.")
    return valor

def cpf(valor):
    valor = re.sub(r"\D", "", str(valor or ""))
    if len(valor) != 11 or valor == valor[0] * 11:
        raise ValueError("CPF inválido.")
    for tamanho in (9, 10):
        soma = sum(int(valor[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(valor[tamanho]):
            raise ValueError("CPF inválido.")
    return valor

def email(valor, obrigatorio=False):
    valor = (valor or "").strip().lower()
    if not valor and not obrigatorio:
        return None
    if not _RE_EMAIL.fullmatch(valor) or len(valor) > 150:
        raise ValueError("E-mail inválido.")
    return valor

def cep(valor):
    valor = re.sub(r"\D", "", str(valor or ""))
    if len(valor) != 8:
        raise ValueError("CEP deve conter 8 números.")
    return valor

def telefone(valor):
    valor = re.sub(r"\D", "", str(valor or ""))
    if not 10 <= len(valor) <= 13:
        raise ValueError("Telefone inválido. Informe DDD e número.")
    return valor

def senha(valor):
    if not isinstance(valor, str) or len(valor.encode("utf-8")) > 72 or len(valor) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres e no máximo 72 bytes.")
    if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("A senha deve conter letras e números.")
    return valor

def dinheiro(valor, campo="valor", permitir_zero=True):
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError, AttributeError):
        raise ValueError(f"{campo.capitalize()} inválido.")
    if not numero.is_finite() or numero < 0 or (not permitir_zero and numero == 0):
        raise ValueError(f"{campo.capitalize()} deve ser um valor válido e não negativo.")
    if numero.as_tuple().exponent < -2:
        raise ValueError(f"{campo.capitalize()} pode ter no máximo duas casas decimais.")
    return numero.quantize(Decimal("0.01"))
