from datetime import datetime
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

def agora():
    return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)
