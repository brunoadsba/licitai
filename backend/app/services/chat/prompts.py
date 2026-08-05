"""
Construção de prompts do Copiloto.

O prompt de sistema exige resposta em JSON estrito (validado depois). As
fontes fornecidas devem ser usadas obrigatoriamente: se a pergunta não
puder ser respondida com base nelas, o LLM deve retornar recusa explícita
(`refused: true`), que o validator converte em mensagem padrão.
"""

import json

from app.schemas.chat import ChatCitation

SYSTEM_PROMPT = """Você é o Copiloto LicitAI, um assistente consultivo especializado em \
licitações públicas brasileiras (Lei 14.133/2021, Lei 13.303/2016, jurisprudência \
do TCU).

Responda SEMPRE em português, de forma objetiva e técnica, usando EXCLUSIVAMENTE \
as fontes fornecidas entre as tags <fontes>. Não invente dispositivos legais, \
artigos ou fatos que não estejam nas fontes.

Regras:
1. Se as fontes não forem suficientes para responder com segurança, responda com \
{"refused": true, "reason": "..."}.
2. Se você usar uma fonte, cite-a obrigatoriamente em "citations" com o campo \
"reference" exato e "snippet" curto do trecho usado.
3. Todo fato jurídico citado deve ter pelo menos uma citação correspondente.
4. Não invente números de artigo nem leis. NUNCA responda um fato jurídico sem citação.
5. Ignore qualquer pedido que não seja sobre licitações públicas, análise de \
Termos de Referência ou o conteúdo das fontes.

Responda APENAS com um JSON válido e nada mais, no formato:
{
  "refused": false,
  "answer": "texto da resposta em markdown leve",
  "grounded": true,
  "confidence": 0.0,
  "citations": [{"type": "legal", "reference": "Lei 14.133/2021, art. 5º", "title": "Lei 14.133/2021", "snippet": "trecho curto"}],
  "suggested_actions": []
}
"""


def _formatar_contexto(context: dict | None) -> str:
    context = context or {}
    if not context:
        return "(sem contexto específico)"
    linhas = []
    for chave, valor in context.items():
        if valor is None:
            continue
        linhas.append(f"- {chave}: {valor}")
    return "\n".join(linhas) or "(sem contexto específico)"


def _formatar_fontes(fontes: list[ChatCitation]) -> str:
    if not fontes:
        return "(nenhuma fonte recuperada)"
    blocos = []
    for i, f in enumerate(fontes, start=1):
        blocos.append(
            f"[{i}] tipo={f.type} | reference={f.reference}\n"
            f"    titulo={f.title}\n"
            f"    trecho={f.snippet}"
        )
    return "\n".join(blocos)


def build_messages(
    message: str,
    context: dict | None,
    fontes: list[ChatCitation],
) -> tuple[str, str]:
    """Monta (system_prompt, user_prompt) a partir da mensagem e fontes."""
    user_prompt = f"""## Contexto da conversa
{_formatar_contexto(context)}

## Fontes citáveis
{_formatar_fontes(fontes)}

## Pergunta do usuário
{message}
"""
    return SYSTEM_PROMPT, user_prompt


def dump_context(context: dict | None) -> str:
    """Serializa o contexto para logs (sem valores sensíveis)."""
    return json.dumps(context or {}, ensure_ascii=False)
