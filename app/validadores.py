import re
from decimal import Decimal, InvalidOperation

_RE_PLACA = re.compile(r"^(?:[A-Z]{3}[0-9][A-Z0-9][0-9]{2})$")
_RE_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def texto(valor, campo, minimo=1, maximo=255, permitir_arroba=False):
    """Valida um texto livre. O símbolo @ só é aceito quando o chamador autoriza (campo de e-mail)."""
    if not isinstance(valor, str):
        raise ValueError(f"Informe {campo}.")
    valor = valor.strip()
    if len(valor) < minimo or len(valor) > maximo:
        raise ValueError(f"{campo.capitalize()} deve ter entre {minimo} e {maximo} caracteres.")
    if not permitir_arroba and "@" in valor:
        raise ValueError(f"{campo.capitalize()} não pode conter @. Use esse símbolo apenas no campo de e-mail.")
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


# --- Pessoa física / jurídica ------------------------------------------------
TIPOS_PESSOA = ("fisica", "juridica")


def cnpj(valor):
    """Valida CNPJ numérico (14 dígitos) conferindo os dois dígitos verificadores."""
    valor = re.sub(r"\D", "", str(valor or ""))
    if len(valor) != 14 or valor == valor[0] * 14:
        raise ValueError("CNPJ inválido.")
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for _ in range(2):
        soma = sum(int(d) * p for d, p in zip(valor, pesos))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(valor[len(pesos)]):
            raise ValueError("CNPJ inválido.")
        pesos = [6] + pesos
    return valor


def tipo_pessoa(valor):
    """Normaliza o tipo de pessoa. Sem valor informado, assume pessoa física."""
    valor = str(valor or "fisica").strip().lower()
    if valor not in TIPOS_PESSOA:
        raise ValueError("Tipo de pessoa inválido. Use fisica ou juridica.")
    return valor


def documento(tipo, valor):
    """Valida CPF (pessoa física) ou CNPJ (pessoa jurídica) e devolve só os dígitos."""
    return cnpj(valor) if tipo == "juridica" else cpf(valor)


def documento_livre(valor):
    """Aceita CPF ou CNPJ, descobrindo pelo tamanho. Usado no recibo, quando o cliente não é cadastrado."""
    digitos = re.sub(r"\D", "", str(valor or ""))
    if len(digitos) == 11:
        return cpf(digitos)
    if len(digitos) == 14:
        return cnpj(digitos)
    raise ValueError("Informe um CPF (11 dígitos) ou um CNPJ (14 dígitos).")


def formatar_documento(valor):
    """000.000.000-00 ou 00.000.000/0000-00; devolve o texto original se o tamanho não for reconhecido."""
    d = re.sub(r"\D", "", str(valor or ""))
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return str(valor or "")


def intervalo_iso(inicio, fim, campo="período"):
    """Converte duas datas AAAA-MM-DD em objetos date, garantindo inicio <= fim."""
    from datetime import date
    try:
        ini = date.fromisoformat(str(inicio))
        final = date.fromisoformat(str(fim))
    except (TypeError, ValueError):
        raise ValueError(f"Informe o {campo} no formato AAAA-MM-DD.")
    if final < ini:
        raise ValueError("A data final não pode ser anterior à data inicial.")
    if (final - ini).days > 366:
        raise ValueError("O período máximo permitido é de 366 dias.")
    return ini, final
