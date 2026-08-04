"""
Comparador determinístico entre Termo de Referência e propostas.

Para cada regra do molde:
1. Extrai o valor esperado no TR (valor_tr).
2. Extrai o valor na proposta (valor_proposta).
3. Classifica o resultado: ok / falha / atencao.

Classificação:
- numero_inteiro / numero_extenso / percentual / monetario:
  igual → ok; diferente → falha; valor_tr ausente → atencao.
- data: igual (normalizada ISO) → ok; diferente → falha; valor_tr ausente → atencao.
- booleano: presente na proposta → ok; ausente → falha;
  valor_tr ausente → atencao.
- legal: lei/artigo citado na proposta → ok; não citado → falha;
  valor_tr ausente → atencao.
"""

import logging

from app.services.rules.extractor import extrair_valor

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_FALHA = "falha"
STATUS_ATENCAO = "atencao"

TIPOS_NUMERICOS = {
    "numero_inteiro",
    "numero_extenso",
    "percentual",
    "monetario",
}


def _texto_documento(itens: list[dict]) -> str:
    """Concatena o texto completo de um documento (título + conteúdo)."""
    partes = []
    for item in itens:
        titulo = item.get("title") or ""
        conteudo = item.get("content") or ""
        partes.append(f"{titulo}\n{conteudo}")
    return "\n\n".join(partes)


def _normalizar_numero(valor) -> float | None:
    """Converte o valor extraído em número comparável (int/float/string BR)."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        raw = str(valor).strip()
        if "," in raw and "." in raw:
            if raw.rfind(",") > raw.rfind("."):
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(",", ".")
        return float(raw)
    except (TypeError, ValueError):
        return None


def comparar_regra(
    regra: dict,
    valor_tr,
    valor_proposta,
) -> dict:
    """
    Classifica uma regra para uma proposta.

    Returns:
        Dict com status, motivo, valor_tr, valor_proposta.
    """
    base = {
        "valor_tr": _texto_valor(valor_tr),
        "valor_proposta": _texto_valor(valor_proposta),
    }

    if valor_tr is None:
        base.update({
            "status": STATUS_ATENCAO,
            "motivo": "Valor esperado não encontrado no Termo de Referência; "
                      "não é possível validar a conformidade.",
        })
        return base

    tipo = regra.get("tipo")

    if tipo in TIPOS_NUMERICOS:
        tr_num = _normalizar_numero(valor_tr)
        prop_num = _normalizar_numero(valor_proposta)
        if prop_num is None:
            base.update({
                "status": STATUS_FALHA,
                "motivo": "Valor não localizado na proposta do fornecedor.",
            })
        elif tr_num == prop_num:
            base.update({
                "status": STATUS_OK,
                "motivo": "Valor confere com o Termo de Referência.",
            })
        else:
            base.update({
                "status": STATUS_FALHA,
                "motivo": f"Valor da proposta ({valor_proposta}) diverge do "
                          f"esperado no Termo de Referência ({valor_tr}).",
            })
        return base

    # data, cnpj, prazo_relativo, cep: comparação textual normalizada
    if tipo in ("data", "cnpj", "prazo_relativo", "cep"):
        if not valor_proposta:
            base.update({
                "status": STATUS_FALHA,
                "motivo": f"{tipo.replace('_', ' ').title()} não localizado(a) na proposta do fornecedor.",
            })
        elif str(valor_tr).strip().lower() == str(valor_proposta).strip().lower():
            base.update({
                "status": STATUS_OK,
                "motivo": "Valor confere com o Termo de Referência.",
            })
        else:
            base.update({
                "status": STATUS_FALHA,
                "motivo": f"Valor da proposta ({valor_proposta}) diverge do "
                          f"esperado no Termo de Referência ({valor_tr}).",
            })
        return base

    # booleano / legal: presença binária
    if valor_proposta is True:
        base.update({
            "status": STATUS_OK,
            "motivo": "Item exigido está presente na proposta.",
        })
    elif valor_proposta is False:
        base.update({
            "status": STATUS_FALHA,
            "motivo": "Item exigido não consta na proposta do fornecedor.",
        })
    else:
        base.update({
            "status": STATUS_FALHA,
            "motivo": "Não foi possível confirmar o item exigido na proposta.",
        })
    return base


def _texto_valor(valor) -> str | None:
    """Converte valor extraído em representação textual para persistir."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    return str(valor)


async def comparar(
    regras: list[dict],
    itens_tr: list[dict],
    propostas: list[dict],
) -> list[dict]:
    """
    Executa a comparação de todas as regras para todas as propostas.

    Args:
        regras: lista de regras (model_dump) do molde.
        itens_tr: itens estruturados do TR.
        propostas: lista de dicts com {"fornecedor_id", "itens"}.

    Returns:
        Lista de dicts:
        {
            "fornecedor_id", "regra_id", "status", "motivo",
            "valor_tr", "valor_proposta"
        }
    """
    resultados = []
    for regra in regras:
        valor_tr = extrair_valor(regra, itens_tr)
        for proposta in propostas:
            fornecedor_id = proposta["fornecedor_id"]
            valor_proposta = extrair_valor(regra, proposta["itens"])
            resultado = comparar_regra(regra, valor_tr, valor_proposta)
            resultados.append({
                "fornecedor_id": fornecedor_id,
                "regra_id": regra["id"],
                "status": resultado["status"],
                "motivo": resultado["motivo"],
                "valor_tr": resultado["valor_tr"],
                "valor_proposta": resultado["valor_proposta"],
            })
    return resultados
