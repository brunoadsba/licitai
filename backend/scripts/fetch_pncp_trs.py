"""Spike PNCP: lista TRs/PBs públicos da CODEBA; baixa PDF só com --apply.

Default é dry-run (só lê e imprime, não grava binário). Sem LLM, sem worker,
sem upload. Respeita o rate limit do PNCP (pausa + backoff no client).

Uso:
    PYTHONPATH=backend python backend/scripts/fetch_pncp_trs.py --de 20240101 --ate 20260928
    PYTHONPATH=backend python backend/scripts/fetch_pncp_trs.py --cnpj 14372148000161 --de 20240101 --ate 20260928 --apply --max-downloads 50
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.services.pncp.client import (  # noqa: E402
    TIPOS_ALVO_DEFAULT,
    USER_AGENT,
    ResultadoDryRun,
    baixar,
    listar_arquivos,
    listar_contratacoes,
    nome_arquivo,
    sha256_bytes,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DEST_PADRAO = Path("fixtures/trs-codeba/pendente/pncp")


def janelas_anuais(de: str, ate: str) -> list[tuple[str, str]]:
    anos = range(int(de[:4]), int(ate[:4]) + 1)
    return [
        (f"{a}0101" if f"{a}0101" > de else de,
         f"{a}1231" if f"{a}1231" < ate else ate)
        for a in anos
    ]


async def dry_run(client: httpx.AsyncClient, args) -> ResultadoDryRun:
    resultado = ResultadoDryRun()
    for cnpj in args.cnpj:
        for inicio, fim in janelas_anuais(args.de, args.ate):
            contratacoes = await listar_contratacoes(
                client, cnpj=cnpj, data_inicial=inicio, data_final=fim,
                pausa=args.pausa,
            )
        for contratacao in contratacoes:
            resultado.contratacoes.append(contratacao)
            if contratacao.orgao:
                logger.info("Órgão: %s (%s)", contratacao.orgao, contratacao.cnpj)
            for arquivo in await listar_arquivos(client, contratacao, pausa=args.pausa):
                resultado.tipos_vistos[arquivo.tipo_id or -1] = (
                    resultado.tipos_vistos.get(arquivo.tipo_id or -1, 0) + 1
                )
                if arquivo.tipo_id in TIPOS_ALVO_DEFAULT and arquivo.url:
                    resultado.arquivos_alvo.append((contratacao, arquivo))
    return resultado


def carregar_manifest(dest: Path) -> tuple[set[str], set[str]]:
    manifest = dest / "manifest.jsonl"
    hashes: set[str] = set()
    urls: set[str] = set()
    if manifest.exists():
        for linha in manifest.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(linha)
                hashes.add(item.get("sha256", ""))
                urls.add(item.get("url", ""))
            except json.JSONDecodeError:
                continue
    hashes.discard("")
    urls.discard("")
    return hashes, urls


async def apply(client: httpx.AsyncClient, args, resultado: ResultadoDryRun) -> int:
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    vistos, urls_vistas = carregar_manifest(dest)
    manifest = open(dest / "manifest.jsonl", "a", encoding="utf-8")  # noqa: PTH123
    baixados = 0
    try:
        for contratacao, arquivo in resultado.arquivos_alvo:
            if args.max_downloads and baixados >= args.max_downloads:
                break
            if arquivo.url in urls_vistas:
                logger.info("Dedupe (URL já no manifesto): %s", arquivo.url)
                continue
            dados = await baixar(client, arquivo.url, pausa=args.pausa)
            digest = sha256_bytes(dados)
            if digest in vistos:
                logger.info("Dedupe (hash já no manifesto): %s", arquivo.url)
                continue
            nome = nome_arquivo(contratacao, arquivo)
            (dest / nome).write_bytes(dados)
            manifest.write(json.dumps({
                "cnpj": contratacao.cnpj, "ano": contratacao.ano,
                "sequencial": contratacao.sequencial,
                "tipo": arquivo.tipo_id, "tipo_nome": arquivo.tipo_nome,
                "titulo": arquivo.titulo, "url": arquivo.url,
                "sha256": digest, "path": nome,
            }, ensure_ascii=False) + "\n")
            vistos.add(digest)
            baixados += 1
            logger.info("Baixado %s (%d bytes)", nome, len(dados))
    finally:
        manifest.close()
    return baixados


async def main() -> None:
    p = argparse.ArgumentParser(description="Spike: TRs públicos da CODEBA no PNCP")
    p.add_argument("--cnpj", action="append", default=["14372148000161"])
    p.add_argument("--de", required=True)
    p.add_argument("--ate", required=True)
    p.add_argument("--apply", action="store_true", help="grava PDFs (default: dry-run)")
    p.add_argument("--max-downloads", type=int, default=50)
    p.add_argument("--dest", default=str(DEST_PADRAO))
    p.add_argument("--pausa", type=float, default=1.5, help="segundos entre chamadas")
    args = p.parse_args()

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=30.0
    ) as client:
        resultado = await dry_run(client, args)

    print(f"contratações: {len(resultado.contratacoes)} | "
          f"arquivos TR/PB: {len(resultado.arquivos_alvo)} | "
          f"tipos vistos: {sorted(resultado.tipos_vistos.items())}")
    for contratacao, arquivo in resultado.arquivos_alvo[:20]:
        print(f"  [{arquivo.tipo_id}] {contratacao.ano}/{contratacao.sequencial} "
              f"{arquivo.titulo[:80]}")
    if not args.apply:
        print("dry-run: nada gravado (use --apply para baixar)")
        return
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, timeout=60.0
    ) as client:
        n = await apply(client, args, resultado)
    print(f"baixados: {n} em {args.dest}")


if __name__ == "__main__":
    asyncio.run(main())
