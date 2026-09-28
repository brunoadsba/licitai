"""Cliente da API pública do PNCP (consulta, sem token).

Só leitura de documentos já publicados. Sem LLM, sem worker, sem escrita
fora do manifesto/PDFs em modo --apply. Respeito ao rate limit: pausa entre
chamadas + backoff exponencial com jitter em 429/503.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

BASE_CONSULTA = "https://pncp.gov.br/api/consulta"
BASE_ARQUIVOS = "https://pncp.gov.br/api/pncp/v1"
USER_AGENT = "LicitAI-CODEBA-piloto"

MODALIDADES = list(range(1, 14))
TIPOS_ALVO_DEFAULT = frozenset({4, 6})

_slug_re = re.compile(r"[^a-z0-9]+")


@dataclass
class Contratacao:
    cnpj: str
    ano: int
    sequencial: int
    orgao: str = ""
    objeto: str = ""


@dataclass
class ArquivoRemoto:
    url: str
    tipo_id: int | None = None
    tipo_nome: str = ""
    titulo: str = ""


@dataclass
class ResultadoDryRun:
    contratacoes: list[Contratacao] = field(default_factory=list)
    arquivos_alvo: list[tuple[Contratacao, ArquivoRemoto]] = field(default_factory=list)
    tipos_vistos: dict[int, int] = field(default_factory=dict)


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    *,
    pausa: float,
    tentativas: int = 5,
) -> dict | list | None:
    espera = 2.0
    for tentativa in range(1, tentativas + 1):
        resp = await client.get(url, params=params)
        if resp.status_code == 204:
            return None
        if resp.status_code in (429, 503):
            logger.warning(
                "PNCP %s (tentativa %d/%d); esperando %.0fs",
                resp.status_code, tentativa, tentativas, espera,
            )
            await asyncio.sleep(espera + random.uniform(0, 1))
            espera *= 2
            continue
        resp.raise_for_status()
        await asyncio.sleep(pausa)
        return resp.json()
    raise RuntimeError(f"PNCP rate limit persistente em {url}")


def slugify(texto: str, limite: int = 40) -> str:
    slug = _slug_re.sub("-", (texto or "").lower()).strip("-")
    return (slug[:limite].rstrip("-") or "sem-titulo")


def nome_arquivo(contratacao: Contratacao, arquivo: ArquivoRemoto) -> str:
    kind = "tr" if arquivo.tipo_id == 4 else "pb" if arquivo.tipo_id == 6 else f"t{arquivo.tipo_id}"
    return f"{contratacao.ano}-{contratacao.sequencial}-{kind}-{slugify(arquivo.titulo or contratacao.objeto)}.pdf"


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


async def listar_contratacoes(
    client: httpx.AsyncClient,
    *,
    cnpj: str,
    data_inicial: str,
    data_final: str,
    modalidades: list[int] = MODALIDADES,
    tamanho_pagina: int = 50,
    pausa: float = 1.5,
) -> list[Contratacao]:
    achadas: list[Contratacao] = []
    for modalidade in modalidades:
        pagina = 1
        while True:
            payload = await _get_json(
                client,
                f"{BASE_CONSULTA}/v1/contratacoes/publicacao",
                {
                    "dataInicial": data_inicial,
                    "dataFinal": data_final,
                    "codigoModalidadeContratacao": modalidade,
                    "cnpj": cnpj,
                    "pagina": pagina,
                    "tamanhoPagina": tamanho_pagina,
                },
                pausa=pausa,
            )
            if not payload:
                break
            for item in payload.get("data", []):
                orgao = item.get("orgaoEntidade", {}) or {}
                achadas.append(Contratacao(
                    cnpj=cnpj,
                    ano=int(item.get("anoCompra", 0) or 0),
                    sequencial=int(item.get("sequencialCompra", 0) or 0),
                    orgao=str(orgao.get("razaoSocial", "") or ""),
                    objeto=str(item.get("objetoCompra", "") or ""),
                ))
            if pagina >= int(payload.get("totalPaginas", 1) or 1):
                break
            pagina += 1
    return achadas


async def listar_arquivos(
    client: httpx.AsyncClient,
    contratacao: Contratacao,
    *,
    pausa: float = 1.5,
) -> list[ArquivoRemoto]:
    payload = await _get_json(
        client,
        f"{BASE_ARQUIVOS}/orgaos/{contratacao.cnpj}/compras/"
        f"{contratacao.ano}/{contratacao.sequencial}/arquivos",
        {},
        pausa=pausa,
    )
    arquivos: list[ArquivoRemoto] = []
    for item in payload or []:
        tipo = item.get("tipoDocumentoId")
        try:
            tipo_id = int(tipo) if tipo is not None else None
        except (TypeError, ValueError):
            tipo_id = None
        arquivos.append(ArquivoRemoto(
            url=str(item.get("url", "") or ""),
            tipo_id=tipo_id,
            tipo_nome=str(item.get("tipoDocumentoNome", "") or item.get("nomeTipoDocumento", "") or ""),
            titulo=str(item.get("titulo", "") or item.get("nomeArquivo", "") or ""),
        ))
    return arquivos


async def baixar(client: httpx.AsyncClient, url: str, *, pausa: float = 1.5) -> bytes:
    espera = 2.0
    for _tentativa in range(1, 6):
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code in (429, 503):
            await asyncio.sleep(espera + random.uniform(0, 1))
            espera *= 2
            continue
        resp.raise_for_status()
        await asyncio.sleep(pausa)
        return resp.content
    raise RuntimeError(f"PNCP rate limit persistente no download {url}")
