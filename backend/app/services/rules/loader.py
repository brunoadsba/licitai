"""
Carregamento e validação de moldes de regras (config_json).

O molde é um JSON que descreve regras de conformidade aplicadas a um TR.
Cada regra usa âncoras para localizar informações no documento:
- numero_inteiro: busca o próximo número inteiro após a âncora textual.
- numero_extenso: busca o próximo número por extenso (ex.: "trinta dias").
- booleano: verifica presença/ausência de termos-chave.
- legal: verifica menção a artigos/leis obrigatórias.
- data: busca a próxima data (dd/mm/aaaa) após a âncora.
- percentual: busca o próximo percentual (ex.: "5%") após a âncora.
- monetario: busca o próximo valor em reais (ex.: "R$ 1.500,00").

Formato esperado do config_json:
{
  "versao": 1,
  "regras": [
    {
      "id": "vigencia_dias",
      "rotulo": "Vigência mínima",
      "tipo": "numero_inteiro",
      "ancora": "vigência",
      "unidade": "dias",
      "expectativa": 90
    },
    {
      "id": "garantia_exigida",
      "rotulo": "Garantia",
      "tipo": "booleano",
      "palavras_chave": ["garantia", "caução"]
    },
    {
      "id": "lei_14133",
      "rotulo": "Lei 14.133/2021",
      "tipo": "legal",
      "regex": "14\\.133/2021"
    }
  ]
}
"""

import json
import logging

from pydantic import BaseModel, Field, field_validator, ValidationError

logger = logging.getLogger(__name__)

TIPOS_VALIDOS = {
    "numero_inteiro",
    "numero_extenso",
    "booleano",
    "legal",
    "data",
    "percentual",
    "monetario",
    "cnpj",
    "prazo_relativo",
    "cep",
}


class RegraModel(BaseModel):
    """Definição de uma regra de conformidade."""
    id: str = Field(..., min_length=1, max_length=100)
    rotulo: str = Field(..., min_length=1, max_length=300)
    tipo: str
    ancora: str | None = Field(default=None, max_length=500)
    unidade: str | None = Field(default=None, max_length=50)
    expectativa: float | str | None = None
    palavras_chave: list[str] | None = Field(default=None, max_length=50)
    regex: str | None = Field(default=None, max_length=500)

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido: {v}. Use um de {sorted(TIPOS_VALIDOS)}")
        return v

    @field_validator("palavras_chave")
    @classmethod
    def validar_palavras(cls, v: list[str] | None) -> list[str] | None:
        if not v:
            return None
        return [p.strip() for p in v if p.strip()]


class MoldeModel(BaseModel):
    """Molde completo de regras."""
    versao: int = Field(default=1)
    regras: list[RegraModel] = Field(..., min_length=1)

    @field_validator("regras")
    @classmethod
    def ids_unicos(cls, v: list[RegraModel]) -> list[RegraModel]:
        ids = [r.id for r in v]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de regras devem ser únicos")
        return v


def _json_invalid_error(config_json: str, msg: str) -> ValidationError:
    """Cria um ValidationError padrão Pydantic para JSON inválido."""
    return ValidationError.from_exception_data(
        "MoldeModel",
        [{
            "type": "json_invalid",
            "loc": ("config_json",),
            "msg": f"JSON inválido: {msg}",
            "input": config_json,
            "ctx": {"error": msg},
        }],
    )


def parse_molde(config_json: str) -> MoldeModel:
    """
    Faz o parse e validação do config_json de um molde.

    Raises:
        ValidationError: se o JSON for inválido ou não atender ao schema.
    """
    try:
        data = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise _json_invalid_error(config_json, exc.msg) from exc

    if not isinstance(data, dict):
        raise ValidationError.from_exception_data(
            "MoldeModel",
            [{"loc": ("config_json",), "msg": "config_json deve ser um objeto", "type": "type_error", "input": type(data).__name__}],
        )

    return MoldeModel.model_validate(data)


def registrar_erro(rules: list[dict], regra: RegraModel, motivo: str) -> dict:
    """Cria um resultado de regra não avaliada (FALHA por indisponibilidade)."""
    return {
        "regra_id": regra.id,
        "status": "falha",
        "motivo": motivo,
        "valor_tr": None,
        "valor_proposta": None,
    }
