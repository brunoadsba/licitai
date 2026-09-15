"""
Mascaramento de PII em logs/exceções (piloto CODEBA, dado sigiloso fica local).

Cobre CPF, e-mail, telefone BR e headers de auth. Usado pelo JsonFormatter
antes de serializar; Sentry segue OFF por default (sem DSN = no-op).
"""

import re

_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")
_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE = re.compile(r"\b(?:\+55\s?)?(?:\(?\d{2}\)?[\s-]?)?\d{4,5}[\s-]?\d{4}\b")
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/=]+", re.IGNORECASE)
_TOKEN_KV = re.compile(r"((?:api[_-]?token|x-api-token|password|senha)\s*[:=]\s*)['\"]?[^'\"\s,}]+", re.IGNORECASE)


def scrub(text: str) -> str:
    if not text:
        return text
    text = _EMAIL.sub("[email]", text)
    text = _CPF.sub("[cpf]", text)
    text = _BEARER.sub(r"\1[redacted]", text)
    text = _TOKEN_KV.sub(r"\1[redacted]", text)
    # Telefone por último (padrão mais genérico); evita mascarar anos/ids curtos.
    text = _PHONE.sub("[tel]", text)
    return text
