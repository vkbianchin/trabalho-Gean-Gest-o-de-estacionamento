"""Senha de uso único baseada em tempo (TOTP, RFC 6238) usando só a biblioteca padrão.

Compatível com Google Authenticator, Microsoft Authenticator, Authy etc. (SHA-1, 6 dígitos, 30 s).
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PASSO_SEGUNDOS = 30
DIGITOS = 6


def gerar_segredo():
    """Segredo aleatório de 160 bits em Base32 (32 caracteres)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _chave(segredo):
    limpo = str(segredo).strip().replace(" ", "").upper()
    return base64.b32decode(limpo + "=" * (-len(limpo) % 8))


def codigo_em(segredo, instante=None, digitos=DIGITOS):
    """Código válido no instante informado (segundos desde 1970); sem argumento, usa o relógio atual."""
    contador = int((time.time() if instante is None else instante) // PASSO_SEGUNDOS)
    mac = hmac.new(_chave(segredo), struct.pack(">Q", contador), hashlib.sha1).digest()
    deslocamento = mac[-1] & 0x0F
    numero = struct.unpack(">I", mac[deslocamento:deslocamento + 4])[0] & 0x7FFFFFFF
    return str(numero % 10 ** digitos).zfill(digitos)


def verificar(segredo, codigo, instante=None, janela=1):
    """Confere o código aceitando `janela` passos de tolerância para cada lado (relógios levemente fora de hora)."""
    codigo = "".join(c for c in str(codigo or "") if c.isdigit())
    if len(codigo) != DIGITOS:
        return False
    base = time.time() if instante is None else instante
    aceito = False
    for deslocamento in range(-janela, janela + 1):  # percorre todos para não variar o tempo de resposta
        if hmac.compare_digest(codigo_em(segredo, base + deslocamento * PASSO_SEGUNDOS), codigo):
            aceito = True
    return aceito


def uri_provisionamento(segredo, conta, emissor="ParkFlow"):
    """Endereço otpauth:// que os aplicativos de autenticação entendem (também usado em QR Code)."""
    return (f"otpauth://totp/{quote(emissor)}:{quote(conta)}?secret={segredo}"
            f"&issuer={quote(emissor)}&algorithm=SHA1&digits={DIGITOS}&period={PASSO_SEGUNDOS}")
