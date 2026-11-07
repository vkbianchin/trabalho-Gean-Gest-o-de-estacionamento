from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def agora():
    return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)


def hoje():
    return agora().date()


def minutos_entre(inicio, fim):
    """Minutos inteiros (arredondados para baixo) entre dois datetimes locais."""
    return max(0, int((fim - inicio).total_seconds() // 60))


def formatar_duracao(minutos):
    """Texto curto para exibir permanência: 45min, 2h 05min, 1 dia 3h 10min."""
    minutos = max(0, int(minutos))
    dias, resto = divmod(minutos, 1440)
    horas, mins = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f"{dias} dia" + ("s" if dias > 1 else ""))
    if horas:
        partes.append(f"{horas}h")
    if mins or not partes:
        partes.append(f"{mins:02d}min" if horas or dias else f"{mins}min")
    return " ".join(partes)


def limites_do_periodo(inicio, fim):
    """[00:00 do dia inicial, 00:00 do dia seguinte ao final): facilita filtros com >= e <."""
    return datetime.combine(inicio, datetime.min.time()), datetime.combine(fim + timedelta(days=1), datetime.min.time())


def dias_em_atraso(vencimento, referencia, carencia=0):
    """Dias de atraso depois de descontada a carência. 0 significa que não está em atraso."""
    if isinstance(vencimento, datetime):
        vencimento = vencimento.date()
    if isinstance(referencia, datetime):
        referencia = referencia.date()
    if not isinstance(vencimento, date) or not isinstance(referencia, date):
        return 0
    return max(0, (referencia - vencimento).days - int(carencia or 0))
