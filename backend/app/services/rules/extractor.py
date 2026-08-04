"""
Extração determinística de valores a partir de itens estruturados do documento.

Aplica as âncoras definidas no molde sobre o texto dos itens (document_items),
extraindo valores por tipo de regra:
- numero_inteiro: próximo número após a âncora.
- numero_extenso: próximo número por extenso após a âncora.
- booleano: presença/ausência das palavras-chave.
- legal: presença do regex (artigo/lei).
- data: próxima data (dd/mm/aaaa) após a âncora.
- percentual: próximo percentual (ex.: "5%") após a âncora.
- monetario: próximo valor em reais (ex.: "R$ 1.500,00") após a âncora.

A estratégia: por padrão busca sobre TODO o texto do documento; opcionalmente
a âncora pode restringir a busca a um item específico no formato "n" (ex.: "4.3").
"""

import logging
import re
from typing import Any

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

NUMERO_INTEIRO_RE = re.compile(r"\b(\d{1,4}(?:\.\d{3})*)\b")
LEGAL_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3})*$")
DATA_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
PERCENTUAL_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*%")
MONETARIO_RE = re.compile(r"\bR\$\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b")


def extrair_valor(regra: dict, itens: list[dict]) -> Any | None:
    """
    Extrai o valor esperado pelo tipo de regra.

    Args:
        regra: regra carregada (do loader).
        itens: lista de itens estruturados (document_items).

    Returns:
        Valor extraído ou None se não encontrado.
    """
    texto = _texto_por_ancora(regra.get("ancora"), itens)
    if not texto:
        return None

    tipo = regra.get("tipo")
    if tipo == "numero_inteiro":
        return _extrair_numero(texto)
    if tipo == "numero_extenso":
        return _extrair_numero_extenso(texto)
    if tipo == "booleano":
        return _extrair_booleano(regra.get("palavras_chave"), texto)
    if tipo == "legal":
        return _extrair_legal(regra.get("regex"), texto)
    if tipo == "data":
        return _extrair_data(texto)
    if tipo == "percentual":
        return _extrair_percentual(texto)
    if tipo == "monetario":
        return _extrair_monetario(texto)
    if tipo == "cnpj":
        return _extrair_cnpj(texto)
    if tipo == "prazo_relativo":
        return _extrair_prazo_relativo(texto)
    if tipo == "cep":
        return _extrair_cep(texto)
    return None


def _texto_por_ancora(ancora: str | None, itens: list[dict]) -> str:
    """Concatena o texto dos itens relevantes à âncora."""
    if not itens:
        return ""

    if not ancora:
        return "\n".join(_conteudo_item(i) for i in itens)

    # Âncora numérica (ex.: "4.3") restringe a busca a um item específico.
    if LEGAL_RE.match(ancora.strip()):
        alvo = ancora.strip()
        for item in itens:
            if item.get("item_number") == alvo:
                return _conteudo_item(item)
        return ""

    # Âncora textual: busca o trecho do texto que a contém (primeira ocorrência).
    alvo = ancora.lower()
    for item in itens:
        conteudo = _conteudo_item(item)
        idx = conteudo.lower().find(alvo)
        if idx != -1:
            return conteudo
    return ""


def _conteudo_item(item: dict) -> str:
    titulo = item.get("title") or ""
    conteudo = item.get("content") or ""
    return f"{titulo}\n{conteudo}"


def _extrair_numero(texto: str) -> int | None:
    """Extrai o primeiro número inteiro do texto."""
    for match in NUMERO_INTEIRO_RE.finditer(texto):
        raw = match.group(1).replace(".", "")
        try:
            return int(raw)
        except ValueError:
            continue
    return None


def _extrair_numero_extenso(texto: str) -> int | None:
    """Extrai o primeiro número por extenso do texto."""
    palavras = re.findall(r"[a-záàâãéêíóôõúçü]+", texto.lower())
    for palavra in palavras:
        if palavra in NUMEROS_EXTENSO:
            return NUMEROS_EXTENSO[palavra]
    return None


def _extrair_booleano(palavras_chave: list[str] | None, texto: str) -> bool | None:
    """Retorna True se todas as palavras-chave estiverem presentes."""
    if not palavras_chave:
        return None
    texto_lower = texto.lower()
    todas = all(p.lower() in texto_lower for p in palavras_chave)
    return todas


def _extrair_legal(regex: str | None, texto: str) -> bool | None:
    """Retorna True se o regex (lei/artigo) aparecer no texto."""
    if not regex:
        return None
    try:
        return re.search(regex, texto, re.IGNORECASE) is not None
    except re.error:
        logger.warning("Regex inválida na regra legal: %s", regex)
        return None


def _extrair_data(texto: str) -> str | None:
    """Extrai a primeira data no formato dd/mm/aaaa e retorna ISO aaaa-mm-dd."""
    for match in DATA_RE.finditer(texto):
        dia, mes, ano = match.groups()
        try:
            if 1 <= int(mes) <= 12 and 1 <= int(dia) <= 31:
                return f"{ano}-{int(mes):02d}-{int(dia):02d}"
        except ValueError:
            continue
    return None


def _para_decimal(raw: str) -> float:
    """Converte string numérica BR (vírgula decimal, ponto milhar) em float."""
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
    """Extrai o primeiro percentual do texto."""
    for match in PERCENTUAL_RE.finditer(texto):
        try:
            return _para_decimal(match.group(1))
        except ValueError:
            continue
    return None


def _extrair_monetario(texto: str) -> float | None:
    """Extrai o primeiro valor em reais (R$ 1.500,00) do texto."""
    for match in MONETARIO_RE.finditer(texto):
        try:
            return _para_decimal(match.group(1))
        except ValueError:
            continue
    return None


CNPJ_RE = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})\b")
PRAZO_RELATIVO_RE = re.compile(
    r"\b(\d+|\b(?:um|dois|três|quatro|cinco|seis|sete|oito|nove|dez|quinze|vinte|trinta|sessenta|noventa|cento\s+e\s+oitenta)\b)\s*(?:\([^)]*\))?\s*(dias|meses|anos)\b",
    re.IGNORECASE,
)
CEP_RE = re.compile(r"\b(\d{5}-\d{3}|\d{8})\b")


def _extrair_cnpj(texto: str) -> str | None:
    """Extrai o primeiro CNPJ válido do texto."""
    for match in CNPJ_RE.finditer(texto):
        raw = match.group(1).replace(".", "").replace("/", "").replace("-", "")
        if len(raw) == 14:
            return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"
    return None


def _extrair_prazo_relativo(texto: str) -> str | None:
    """Extrai o primeiro prazo relativo (ex: '30 dias', '12 meses') do texto."""
    match = PRAZO_RELATIVO_RE.search(texto)
    if match:
        valor, unidade = match.group(1).strip(), match.group(2).strip().lower()
        return f"{valor} {unidade}"
    return None


def _extrair_cep(texto: str) -> str | None:
    """Extrai o primeiro CEP do texto."""
    match = CEP_RE.search(texto)
    if match:
        raw = match.group(1).replace("-", "")
        if len(raw) == 8:
            return f"{raw[:5]}-{raw[5:]}"
    return None
