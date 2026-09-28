"""Spike PNCP: tudo mockado (httpx.MockTransport). Zero rede no pytest."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_pncp_trs as cli  # noqa: E402

from app.services.pncp.client import (  # noqa: E402
    ArquivoRemoto,
    Contratacao,
    ResultadoDryRun,
    listar_arquivos,
    listar_contratacoes,
    nome_arquivo,
    sha256_bytes,
    slugify,
)


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _pub(pagina, total, itens):
    return {"data": itens, "totalPaginas": total, "pagina": pagina}


def _contratacao(seq):
    return {
        "anoCompra": 2025, "sequencialCompra": seq,
        "orgaoEntidade": {"razaoSocial": "CIA DOCAS BAHIA"},
        "objetoCompra": "Serviços de PABX",
    }


@pytest.mark.asyncio
async def test_lista_e_pagina_contratacoes():
    chamadas = []

    def handler(request):
        chamadas.append(request.url.params.get("pagina"))
        if request.url.params.get("pagina") == "1":
            return httpx.Response(200, json=_pub(1, 2, [_contratacao(10)]))
        return httpx.Response(200, json=_pub(2, 2, [_contratacao(20)]))

    async with _client(handler) as client:
        out = await listar_contratacoes(
            client, cnpj="14372148000161",
            data_inicial="20250101", data_final="20251231", modalidades=[6], pausa=0,
        )
    assert [c.sequencial for c in out] == [10, 20]
    assert chamadas == ["1", "2"]
    assert out[0].orgao == "CIA DOCAS BAHIA"


@pytest.mark.asyncio
async def test_204_vazio():
    async with _client(lambda request: httpx.Response(204)) as client:
        out = await listar_contratacoes(
            client, cnpj="x", data_inicial="20250101",
            data_final="20251231", modalidades=[6], pausa=0,
        )
    assert out == []


@pytest.mark.asyncio
async def test_arquivos_com_tipo_desconhecido():
    def handler(request):
        return httpx.Response(200, json=[
            {"url": "https://x/tr.pdf", "tipoDocumentoId": 4,
             "tipoDocumentoNome": "Termo de Referência", "titulo": "TR PABX"},
            {"url": "https://x/edital.pdf", "tipoDocumentoId": 1,
             "tipoDocumentoNome": "Edital", "titulo": "Edital"},
            {"url": "https://x/semtipo.pdf", "titulo": "Sem tipo"},
        ])

    async with _client(handler) as client:
        out = await listar_arquivos(
            client, Contratacao(cnpj="x", ano=2025, sequencial=1), pausa=0,
        )
    assert [a.tipo_id for a in out] == [4, 1, None]
    assert out[0].tipo_nome == "Termo de Referência"


@pytest.mark.asyncio
async def test_429_tenta_de_novo():
    tentativas = []

    def handler(request):
        tentativas.append(1)
        if len(tentativas) < 3:
            return httpx.Response(429, text="limite")
        return httpx.Response(200, json=_pub(1, 1, []))

    async with _client(handler) as client:
        out = await listar_contratacoes(
            client, cnpj="x", data_inicial="20250101",
            data_final="20251231", modalidades=[6], pausa=0,
        )
    assert out == []
    assert len(tentativas) == 3


def test_slug_e_nome():
    assert slugify("TR PABX — Salvador/2025!") == "tr-pabx-salvador-2025"
    assert slugify("") == "sem-titulo"
    c = Contratacao(cnpj="x", ano=2025, sequencial=7, objeto="PABX")
    assert nome_arquivo(c, ArquivoRemoto(url="u", tipo_id=4, titulo="TR")) == "2025-7-tr-tr.pdf"
    assert nome_arquivo(c, ArquivoRemoto(url="u", tipo_id=6, titulo="PB")).endswith("-pb-pb.pdf")
    assert "-t9-" in nome_arquivo(c, ArquivoRemoto(url="u", tipo_id=9, titulo="X"))


@pytest.mark.asyncio
async def test_apply_dedupe_e_teto(tmp_path):

    pdf = b"%PDF-fake"
    baixados = []

    def handler(request):
        baixados.append(1)
        return httpx.Response(200, content=pdf)

    c = Contratacao(cnpj="x", ano=2025, sequencial=1, objeto="O")
    (tmp_path / "manifest.jsonl").write_text(
        json.dumps({"sha256": sha256_bytes(pdf), "url": "https://x/1.pdf"}) + "\n",
        encoding="utf-8",
    )
    alvo = [
        (c, ArquivoRemoto(url="https://x/1.pdf", tipo_id=4, titulo="A")),
        (c, ArquivoRemoto(url="https://x/2.pdf", tipo_id=4, titulo="B")),
    ]
    args = SimpleNamespace(max_downloads=10, pausa=0, dest=str(tmp_path))
    async with _client(handler) as client:
        n = await cli.apply(client, args, ResultadoDryRun(arquivos_alvo=alvo))
    assert n == 0
    assert baixados == [1]
    assert list(tmp_path.glob("*.pdf")) == []
