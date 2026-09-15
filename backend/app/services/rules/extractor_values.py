"""
Primitivas de extração por tipo — extraído de `extractor.py` p/ manter ≤300.
"""

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

NUMEROS_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
    "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40,
    "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80,
    "noventa": 90, "cem": 100, "cento": 100, "duzentos": 200,
    "trezentos": 300, "quatrocentos": 400, "quinhentos": 500,
    "seiscentos": 600, "setecentos": 700, "oitocentos": 800,
    "novecentos": 900,
}

NUMERO_INTEIRO_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d{1,9})(?!\d)(?![.,]\d)"
)
LEGAL_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3})*$")
DATA_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
PERCENTUAL_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*%")
MONETARIO_RE = re.compile(
    r"\bR\$\s*(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,3}(?:\.\d{3})+|\d+,\d{2}|\d+)(?!\d)(?![.,]\d)"
)
CNPJ_RE = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})\b")
PRAZO_RELATIVO_RE = re.compile(
    r"\b(\d+|\b(?:um|dois|três|quatro|cinco|seis|sete|oito|nove|dez|quinze|vinte|trinta|sessenta|noventa|cento\s+e\s+oitenta)\b)\s*(?:\([^)]*\))?\s*(dias|meses|anos)\b",
    re.IGNORECASE,
)
CEP_RE = re.compile(r"\b(\d{5}-\d{3}|\d{8})\b")


def _extrair_numero(texto: str) -> int | None:
    for match in NUMERO_INTEIRO_RE.finditer(texto):
        raw = match.group(1).replace(".", "")
        try:
            return int(raw)
        except ValueError:
            continue
    return None


def _extrair_numero_extenso(texto: str) -> int | None:
    trecho = re.sub(r"\s+e\s+", " ", texto.lower())
    palavras = re.findall(r"[a-záàâãéêíóôõúçü]+", trecho)
    for i, palavra in enumerate(palavras):
        if palavra not in NUMEROS_EXTENSO:
            continue
        valor = NUMEROS_EXTENSO[palavra]
        if (
            20 <= valor <= 90
            and i + 1 < len(palavras)
            and palavras[i + 1] in NUMEROS_EXTENSO
            and NUMEROS_EXTENSO[palavras[i + 1]] < 10
        ):
            return valor + NUMEROS_EXTENSO[palavras[i + 1]]
        return valor
    return None


def _extrair_booleano(palavras_chave: list[str] | None, texto: str) -> bool | None:
    if not palavras_chave:
        return None
    texto_lower = texto.lower()
    return all(p.lower() in texto_lower for p in palavras_chave)


def _extrair_legal(regex: str | None, texto: str) -> bool | None:
    if not regex:
        return None
    try:
        return re.search(regex, texto, re.IGNORECASE) is not None
    except re.error:
        logger.warning("Regex inválida na regra legal: %s", regex)
        return None


def _extrair_data(texto: str) -> str | None:
    for match in DATA_RE.finditer(texto):
        dia, mes, ano = (int(g) for g in match.groups())
        try:
            date(ano, mes, dia)
        except ValueError:
            continue
        return f"{ano:04d}-{mes:02d}-{dia:02d}"
    return None


def _para_decimal(raw: str) -> float:
    raw = raw.strip()
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    return float(raw)


def _extrair_percentual(texto: str) -> float | None:
    for match in PERCENTUAL_RE.finditer(texto):
        try:
            return _para_decimal(match.group(1))
        except ValueError:
            continue
    return None


def _extrair_monetario(texto: str) -> float | None:
    for match in MONETARIO_RE.finditer(texto):
        raw = match.group(1)
        if "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(".", "")
        try:
            return float(raw)
        except ValueError:
            continue
    return None


def _cnpj_valido(cnpj: str) -> bool:
    if len(cnpj) != 14 or not cnpj.isdigit() or cnpj == cnpj[0] * 14:
        return False
    def _dv(seq: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(seq, pesos, strict=False))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if _dv(cnpj[:12], p1) != int(cnpj[12]):
        return False
    p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _dv(cnpj[:12] + str(int(cnpj[12])), p2) == int(cnpj[13])


def _extrair_cnpj(texto: str) -> str | None:
    for match in CNPJ_RE.finditer(texto):
        raw = match.group(1).replace(".", "").replace("/", "").replace("-", "")
        if _cnpj_valido(raw):
            return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"
    return None


def _extrair_prazo_relativo(texto: str) -> str | None:
    match = PRAZO_RELATIVO_RE.search(texto)
    if match:
        valor, unidade = match.group(1).strip(), match.group(2).strip().lower()
        return f"{valor} {unidade}"
    return None


def _extrair_cep(texto: str) -> str | None:
    match = CEP_RE.search(texto)
    if match:
        raw = match.group(1).replace("-", "")
        if len(raw) == 8:
            return f"{raw[:5]}-{raw[5:]}"
    return None
