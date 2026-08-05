# PRD Executável Revisado — Copiloto LicitAI v1.1

## 0. Identificação

**Nome:** Copiloto LicitAI  
**Versão do PRD:** 1.1  
**Módulo:** Chat assistivo consultivo  
**Status:** revisado e alinhado ao contexto atual do projeto  
**Prioridade:** P1  
**Dependência:** nenhuma alteração estrutural do núcleo existente  
**Premissa:** usar a infraestrutura atual do LicitAI, sem recriar LLM, RAG, autenticação, logging ou banco.

---

# 1. Objetivo

Implementar um **Copiloto consultivo** dentro do LicitAI para apoiar o usuário na análise de Termos de Referência, correções, base legal e contexto da análise.

O Copiloto deve:

1. Responder perguntas sobre a análise atual.
2. Explicar correções sugeridas pelos agentes.
3. Consultar o corpus jurídico via RAG existente.
4. Retornar respostas fundamentadas com citações.
5. Registrar auditoria de conversas.
6. Permitir feedback do usuário.
7. Recusar respostas sem evidência suficiente.
8. Não executar ações de escrita em dados de negócio.

---

# 2. Objetivo técnico

Criar um módulo novo, isolado e testável:

```text
backend/app/api/chat.py
backend/app/schemas/chat.py
backend/app/models/chat.py
backend/app/services/chat/
frontend/src/components/chat/
```

Integrando com:

```text
backend/app/api/router.py
backend/app/services/llm/provider.py
backend/app/services/rag/retriever.py
backend/app/models/analysis.py
backend/app/models/document.py
frontend/src/lib/api.ts
frontend/src/types/index.ts
```

---

# 3. Premissas extraídas do contexto atual

Este PRD considera o estado atual do projeto:

1. O backend é FastAPI com SQLAlchemy async.
2. O frontend é Next.js 14 App Router com Tailwind CSS.
3. As rotas de auditoria ficam sob `/api/v1`.
4. O frontend usa proxy `/api/*` para o backend.
5. Já existe provider LLM com failover:
   - Gemini;
   - Groq;
   - Ollama.
6. Já existe RAG jurídico com:
   - FTS5 com `remove_diacritics 2`;
   - retrieval híbrido RRF;
   - cache de embeddings.
7. Já existem testes de schema PostgreSQL via `pglast` em:

   ```text
   backend/tests/test_init_sql.py
   ```

8. O banco principal em modo nativo é SQLite.
9. O PostgreSQL é opcional via Docker.
10. Testes unitários não devem depender de chave real de LLM.
11. Testes E2E já usam LLM real e podem falhar por cota free tier.
12. O logging é JSON estruturado via:

   ```text
   backend/app/utils/logging_config.py
   ```

13. O timeout de LLM já é tratado no failover.
14. O projeto possui 126 testes unitários e 17 testes E2E.
15. O `config.py` lê `.env` relativo ao CWD.

---

# 4. Escopo do MVP

## 4.1. Entra no escopo

1. Chat consultivo lateral na análise.
2. Conversas persistidas.
3. Mensagens persistidas.
4. Fontes persistidas.
5. Integração com análise atual.
6. Integração com correções da análise.
7. Integração com itens do documento quando houver contexto.
8. Integração com RAG jurídico.
9. Respostas com citações.
10. Feedback `up`/`down`.
11. Health check do chat.
12. Testes unitários com provider fake.
13. Atualização do `db/init.sql`.
14. Atualização de memória/documentation após implementação.

---

## 4.2. Não entra no escopo

1. Aplicar correções automaticamente.
2. Alterar análise, documento, correção, molde ou comparação.
3. Aprovar/rejeitar correções.
4. Enviar e-mail.
5. Criar novo motor multi-agent.
6. Usar LangGraph.
7. Criar autenticação/RBAC.
8. Criar streaming de resposta no MVP.
9. Criar voz ou chat externo.
10. Adicionar E2E dependente de LLM real.
11. Alterar contratos existentes de API.
12. Alterar `database.py`.
13. Alterar `get_db()`.
14. Alterar providers LLM existentes.
15. Alterar RAG existente.

---

# 5. Contrato de execução para IA

A IA executora deve obedecer obrigatoriamente:

## 5.1. Regras de ouro

1. Não quebrar os 126 testes unitários existentes.
2. Não quebrar o build do frontend.
3. Não adicionar dependência nova sem justificativa.
4. Não alterar `backend/app/database.py`.
5. Não alterar `get_db()`.
6. Não alterar providers LLM existentes.
7. Não alterar o RAG existente.
8. Não criar E2E que dependa de LLM real.
9. Não commitar segredos.
10. Não executar ações de escrita em entidades de negócio.
11. Toda resposta factual deve ter citação válida ou recusa.
12. Testes unitários do chat devem usar provider fake.
13. Usar rotas sob `/api/v1`.
14. Usar logging estruturado existente.
15. Respeitar rate limit e timeout existentes.

---

## 5.2. Ordem de execução

Executar nesta ordem:

1. T0 — Baseline.
2. T1 — Configurações.
3. T2 — Models.
4. T3 — Schemas.
5. T4 — LLM adapter e fake provider.
6. T5 — Source builder.
7. T6 — Prompt builder.
8. T7 — Answer validator.
9. T8 — Chat service.
10. T9 — API e router.
11. T10 — Testes de backend.
12. T11 — `init.sql` e migração.
13. T12 — Frontend types/API.
14. T13 — Frontend components.
15. T14 — Integração na página de análise.
16. T15 — Logging, segurança e revisão final.
17. T16 — Validação final e documentação.

---

# 6. Ambiente e comandos canônicos

## 6.1. Backend — testes

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

Testes específicos do chat:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_chat_validator.py tests\test_chat_api.py -q
```

Testes de schema PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_init_sql.py -v
```

---

## 6.2. Backend — execução manual

A partir da raiz do projeto:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

---

## 6.3. Frontend

```powershell
cd frontend
npm run dev
```

Build:

```powershell
cd frontend
npm run build
```

---

## 6.4. Observação sobre `.env`

O `config.py` lê `.env` relativo ao CWD.

Para execução real do backend com chaves, garantir que as variáveis do `.env` da raiz estejam carregadas no processo.

Para testes unitários do chat, **não depender** de `.env` nem de chaves reais.

---

# 7. Arquitetura alvo

```text
Frontend Next.js
   |
   | /api/v1/chat/*
   v
FastAPI Backend
   |
   |-- app/api/chat.py
   |-- app/services/chat/service.py
   |-- app/services/chat/sources.py
   |-- app/services/chat/prompts.py
   |-- app/services/chat/validator.py
   |-- app/services/chat/llm_adapter.py
   |
   |-- app/services/llm/provider.get_llm_provider()
   |-- app/services/rag/retriever.retrieve()
   |-- app/models/analysis.py
   |-- app/models/document.py
   |-- app/models/chat.py
```

---

# 8. Modelo de dados

Criar:

```text
backend/app/models/chat.py
```

Registrar em:

```text
backend/app/models/__init__.py
```

---

## 8.1. Tabela `chat_conversations`

Campos:

```text
id
title
document_id nullable
analysis_id nullable
context_json JSON default {}
created_at
updated_at
```

---

## 8.2. Tabela `chat_messages`

Campos:

```text
id
conversation_id FK
role
content
sources JSON default []
suggested_actions JSON default []
grounded
confidence
provider
latency_ms
feedback
created_at
```

---

## 8.3. Implementação de referência

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="Conversa LicitAI",
    )

    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    analysis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
    )

    context_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_chat_messages_role",
        ),
        CheckConstraint(
            "feedback IS NULL OR feedback IN ('up', 'down')",
            name="ck_chat_messages_feedback",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    sources: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    suggested_actions: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    grounded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    confidence: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    provider: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    latency_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    feedback: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

---

## 8.4. Critérios de aceite do modelo

1. As tabelas são novas.
2. Nenhuma tabela existente é alterada.
3. O SQLite em modo nativo deve conseguir criar as tabelas.
4. O `create_all` não deve tentar alterar tabelas existentes.
5. Os models devem ser importáveis sem erro.
6. Os models devem ser registrados no pacote de models.

---

# 9. Configurações

Arquivo:

```text
backend/app/config.py
```

Adicionar:

```python
chat_enabled: bool = True
chat_require_grounding: bool = True
chat_top_k_sources: int = 5
chat_max_message_length: int = 4000
chat_max_sources_stored: int = 8
chat_force_fake_provider: bool = False
```

---

## 9.1. Critérios

1. Nenhuma variável nova é obrigatória.
2. Testes não dependem de `.env`.
3. O provider fake pode ser ativado por configuração ou override.
4. Produção usa o provider LLM existente.
5. Nenhuma chave nova é introduzida.

---

# 10. Schemas Pydantic

Criar:

```text
backend/app/schemas/chat.py
```

Seguir Pydantic v2.

---

## 10.1. Schemas de request

```python
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.config import settings


class ChatConversationCreate(BaseModel):
    title: Optional[str] = None
    document_id: Optional[int] = None
    analysis_id: Optional[int] = None
    context: Optional[dict[str, Any]] = None


class ChatMessageCreate(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("message não pode ser vazia")

        if len(value) > settings.chat_max_message_length:
            raise ValueError("message excede o tamanho máximo")

        return value


class ChatFeedbackCreate(BaseModel):
    feedback: Literal["up", "down"]
```

---

## 10.2. Schemas de response

```python
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ChatCitation(BaseModel):
    source_id: str
    type: str
    title: Optional[str] = None
    excerpt: str
    law_number: Optional[str] = None
    article: Optional[str] = None
    item_number: Optional[str] = None
    document_id: Optional[int] = None
    analysis_id: Optional[int] = None
    correction_id: Optional[int] = None


class ChatSuggestedAction(BaseModel):
    type: str
    label: str
    target: Optional[str] = None


class ChatConversationResponse(BaseModel):
    id: int
    title: str
    document_id: Optional[int] = None
    analysis_id: Optional[int] = None
    context_json: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    grounded: bool
    confidence: Optional[str] = None
    citations: list[ChatCitation] = []
    suggested_actions: list[ChatSuggestedAction] = []
    provider: Optional[str] = None
    latency_ms: Optional[int] = None
    feedback: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

# 11. Serviço de LLM

Criar:

```text
backend/app/services/chat/llm_adapter.py
```

---

## 11.1. Objetivo

Encapsular o provider LLM existente para uso no chat.

---

## 11.2. Regras

1. Não alterar `get_llm_provider()`.
2. Não alterar providers Gemini/Groq/Ollama.
3. Usar failover existente.
4. Converter mensagens em prompt textual.
5. Permitir fake provider para testes.
6. Não logar segredos.
7. Não logar chave de API.

---

## 11.3. Contrato

```python
from typing import Protocol


class ChatLLMProvider(Protocol):
    provider_name: str

    async def complete(self, messages: list[dict[str, str]]) -> str:
        ...
```

---

## 11.4. Implementação de referência

```python
import json

from app.config import settings
from app.services.llm.provider import get_llm_provider


class FakeChatLLM:
    provider_name = "fake-chat"

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return json.dumps(
            {
                "answer": "Resposta fake para testes.",
                "confidence": "medium",
                "citations": [],
                "suggested_actions": [],
                "warnings": [],
            },
            ensure_ascii=False,
        )


class ExistingChatLLM:
    provider_name = "existing-llm"

    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider

    async def complete(self, messages: list[dict[str, str]]) -> str:
        prompt = "\n\n".join(
            f"[{message['role'].upper()}]\n{message['content']}"
            for message in messages
        )

        provider = self._get_provider()

        return await provider.generate(prompt)


def get_chat_llm():
    if settings.chat_force_fake_provider:
        return FakeChatLLM()

    return ExistingChatLLM()
```

> Se o provider real expuser outro método além de `generate`, adaptar o `ExistingChatLLM` ao contrato real sem alterar o provider.

---

# 12. Serviço de fontes

Criar:

```text
backend/app/services/chat/sources.py
```

---

## 12.1. Objetivo

Montar a lista de fontes que fundamentará a resposta.

---

## 12.2. Formato interno de fonte

```python
from typing import Optional

from pydantic import BaseModel


class ChatSource(BaseModel):
    source_id: str
    type: str
    title: Optional[str] = None
    excerpt: str
    law_number: Optional[str] = None
    article: Optional[str] = None
    item_number: Optional[str] = None
    document_id: Optional[int] = None
    analysis_id: Optional[int] = None
    correction_id: Optional[int] = None
```

---

## 12.3. Tipos de fonte

| Tipo | Origem |
|---|---|
| `legal` | chunks jurídicos via RAG |
| `analysis` | análise atual |
| `correction` | correções da análise |
| `document_item` | item do documento |

---

## 12.4. Função principal

```python
async def build_sources(
    db,
    conversation,
    message: str,
    top_k: int,
) -> list[ChatSource]:
    sources: list[ChatSource] = []

    if conversation.analysis_id:
        sources.extend(await analysis_sources(db, conversation.analysis_id))

    if conversation.analysis_id:
        sources.extend(
            await correction_sources(
                db,
                conversation.analysis_id,
                top_k,
            )
        )

    if conversation.document_id:
        sources.extend(
            await document_item_sources(
                db,
                conversation.document_id,
                conversation.context_json or {},
                message,
                top_k,
            )
        )

    sources.extend(
        await legal_sources(
            db,
            message,
            top_k,
        )
    )

    return dedupe_sources(sources)[: settings.chat_max_sources_stored]
```

---

## 12.5. Fonte legal

Requisitos:

1. Usar o retriever existente em:

   ```text
   backend/app/services/rag/retriever.py
   ```

2. Não recriar busca FTS ou semântica.
3. Tratar exceção e retornar lista vazia se o RAG falhar.
4. Gerar `source_id` estável.

Exemplo conceitual:

```python
async def legal_sources(db, message: str, top_k: int) -> list[ChatSource]:
    try:
        chunks = await retrieve(db, message, top_k=top_k)
    except Exception:
        logger.exception("Falha ao recuperar fontes jurídicas para o chat")
        return []

    sources: list[ChatSource] = []

    for chunk in chunks:
        chunk_id = str(
            getattr(chunk, "id", None)
            or getattr(chunk, "chunk_id", None)
            or ""
        )

        excerpt = str(
            getattr(chunk, "chunk_text", None)
            or getattr(chunk, "text", None)
            or ""
        )[:1000]

        if not chunk_id:
            chunk_id = sha256_hash(excerpt)

        sources.append(
            ChatSource(
                source_id=f"legal:{chunk_id}",
                type="legal",
                title=getattr(chunk, "law_number", None),
                excerpt=excerpt,
                law_number=getattr(chunk, "law_number", None),
                article=getattr(chunk, "article", None),
            )
        )

    return sources
```

---

## 12.6. Fonte de análise

Buscar a análise atual sem lazy loading perigoso.

Exemplo:

```python
async def analysis_sources(db, analysis_id: int) -> list[ChatSource]:
    analysis = await db.get(Analysis, analysis_id)

    if not analysis:
        return []

    excerpt = (
        f"Análise {analysis.id} "
        f"do documento {analysis.document_id}."
    )

    return [
        ChatSource(
            source_id=f"analysis:{analysis.id}",
            type="analysis",
            title="Análise atual",
            excerpt=excerpt[:1000],
            analysis_id=analysis.id,
            document_id=getattr(analysis, "document_id", None),
        )
    ]
```

---

## 12.7. Fonte de correções

As correções são fontes prioritárias.

Devem incluir, quando existirem:

- texto original;
- texto corrigido;
- justificativa;
- fundamentação legal;
- gravidade;
- risco;
- categoria;
- `agent_origin`;
- `review_status`.

Exemplo conceitual:

```python
async def correction_sources(db, analysis_id: int, top_k: int) -> list[ChatSource]:
    result = await db.execute(
        select(Correction)
        .where(Correction.analysis_id == analysis_id)
        .order_by(Correction.id)
        .limit(top_k)
    )

    corrections = result.scalars().all()
    sources: list[ChatSource] = []

    for correction in corrections:
        original = str(getattr(correction, "original_text", "") or "")
        corrected = str(getattr(correction, "corrected_text", "") or "")
        justification = str(getattr(correction, "justification", "") or "")
        legal_basis = str(getattr(correction, "legal_basis", "") or "")

        excerpt = (
            f"DE: {original}\n"
            f"PARA: {corrected}\n"
            f"Justificativa: {justification}\n"
            f"Fundamentação: {legal_basis}"
        )[:1000]

        sources.append(
            ChatSource(
                source_id=f"correction:{correction.id}",
                type="correction",
                title="Correção sugerida",
                excerpt=excerpt,
                analysis_id=analysis_id,
                correction_id=correction.id,
            )
        )

    return sources
```

---

## 12.8. Fonte de item do documento

Se `context_json` possuir `item_number`, buscar o item correspondente.

Exemplo:

```python
async def document_item_sources(
    db,
    document_id: int,
    context: dict,
    message: str,
    top_k: int,
) -> list[ChatSource]:
    item_number = context.get("item_number")

    if not item_number:
        return []

    result = await db.execute(
        select(DocumentItem)
        .where(DocumentItem.document_id == document_id)
        .where(DocumentItem.item_number == item_number)
        .limit(1)
    )

    item = result.scalar_one_or_none()

    if not item:
        return []

    excerpt = str(getattr(item, "content", "") or "")[:1000]

    return [
        ChatSource(
            source_id=f"doc:{document_id}:item:{item_number}",
            type="document_item",
            title=f"Item {item_number}",
            excerpt=excerpt,
            item_number=item_number,
            document_id=document_id,
        )
    ]
```

---

## 12.9. Critérios de aceite do source builder

1. Nenhuma query usa lazy loading fora do contexto async.
2. Falha no RAG não derruba o chat.
3. Fontes possuem `source_id` único.
4. Trechos são truncados.
5. A lista final é limitada.
6. Fontes duplicadas são removidas.
7. Se não houver fonte, retorna lista vazia.

---

# 13. Prompt builder

Criar:

```text
backend/app/services/chat/prompts.py
```

---

## 13.1. System prompt

```python
SYSTEM_PROMPT = """
Você é o Copiloto do LicitAI, assistente especializado em análise de Termos de Referência de licitações públicas.

Regras obrigatórias:
1. Responda somente com JSON válido.
2. Não use markdown.
3. Não invente leis, artigos, itens, correções ou fatos.
4. Use somente as fontes fornecidas.
5. Se não houver fonte suficiente, responda que não encontrou evidência suficiente.
6. Cite fontes usando source_id.
7. Não emita parecer jurídico definitivo.
8. Não sugira ações que alterem dados.
9. Seja objetivo, profissional e auditável.

Formato obrigatório:
{
  "answer": "resposta textual",
  "confidence": "low | medium | high",
  "citations": [
    {
      "source_id": "id_da_fonte",
      "excerpt": "trecho curto opcional"
    }
  ],
  "suggested_actions": [],
  "warnings": []
}
"""
```

---

## 13.2. User prompt

```python
import json


def build_messages(
    message: str,
    context: dict,
    sources: list[dict],
) -> list[dict[str, str]]:
    user_content = f"""
Contexto da conversa:
{json.dumps(context, ensure_ascii=False)}

Fontes disponíveis:
{json.dumps(sources, ensure_ascii=False)}

Pergunta do usuário:
{message}

Responda somente com JSON válido, sem markdown.
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
```

---

# 14. Validador de resposta

Criar:

```text
backend/app/services/chat/validator.py
```

---

## 14.1. Objetivo

Validar a resposta bruta do LLM e garantir grounding.

---

## 14.2. Regras

1. Aceitar JSON válido.
2. Tentar extrair JSON de texto com lixo ao redor.
3. Remover citações com `source_id` inexistente.
4. Se `chat_require_grounding=True` e não houver citação válida, recusar.
5. Normalizar `confidence`.
6. Retornar resposta segura se JSON inválido.
7. Não confiar em `suggested_actions` vindas do modelo.
8. No MVP, descartar `suggested_actions`.

---

## 14.3. Texto padrão de recusa

```python
REFUSAL_MESSAGE = (
    "Não encontrei evidência suficiente na base indexada para responder com segurança. "
    "Revise o documento, a análise ou a base legal correspondente."
)
```

---

## 14.4. Implementação de referência

```python
import json
import re
from dataclasses import dataclass, field


@dataclass
class ValidatedAnswer:
    answer: str
    confidence: str
    citation_source_ids: list[str] = field(default_factory=list)
    suggested_actions: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    grounded: bool = False


def _extract_json(raw: str) -> dict:
    text = raw.strip()

    if "```" in text:
        text = re.sub(r"```(?:json)?", "", text)
        text = text.replace("```", "")

    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("JSON não encontrado")


def validate_llm_answer(
    raw: str,
    valid_source_ids: set[str],
    require_grounding: bool,
) -> ValidatedAnswer:
    try:
        data = _extract_json(raw)
    except Exception:
        return ValidatedAnswer(
            answer=REFUSAL_MESSAGE,
            confidence="low",
            citation_source_ids=[],
            suggested_actions=[],
            warnings=["Resposta do modelo não era JSON válido"],
            grounded=False,
        )

    answer = str(data.get("answer", "")).strip()
    confidence = str(data.get("confidence", "medium")).lower()

    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    raw_citations = data.get("citations", []) or []
    citation_source_ids: list[str] = []

    for citation in raw_citations:
        if not isinstance(citation, dict):
            continue

        source_id = citation.get("source_id")

        if source_id in valid_source_ids:
            citation_source_ids.append(str(source_id))

    warnings = list(data.get("warnings", []) or [])

    if require_grounding and not citation_source_ids:
        return ValidatedAnswer(
            answer=REFUSAL_MESSAGE,
            confidence="low",
            citation_source_ids=[],
            suggested_actions=[],
            warnings=warnings + ["Sem fontes suficientes"],
            grounded=False,
        )

    if not answer:
        return ValidatedAnswer(
            answer=REFUSAL_MESSAGE,
            confidence="low",
            citation_source_ids=citation_source_ids,
            suggested_actions=[],
            warnings=warnings + ["Resposta vazia"],
            grounded=bool(citation_source_ids),
        )

    return ValidatedAnswer(
        answer=answer[:5000],
        confidence=confidence,
        citation_source_ids=citation_source_ids,
        suggested_actions=[],
        warnings=warnings,
        grounded=bool(citation_source_ids),
    )
```

---

# 15. Chat service

Criar:

```text
backend/app/services/chat/service.py
```

---

## 15.1. Responsabilidades

1. Buscar conversa.
2. Validar mensagem.
3. Construir fontes.
4. Montar prompt.
5. Chamar LLM.
6. Validar resposta.
7. Persistir mensagem do usuário.
8. Persistir mensagem do assistente.
9. Registrar latência e provider.
10. Tratar falhas com resposta segura.

---

## 15.2. Fluxo obrigatório

```text
1. Receber conversation_id e message.
2. Buscar ChatConversation.
3. Se não existir, retornar 404.
4. Se chat_enabled=False, retornar 503.
5. Trimar e validar message.
6. Construir fontes.
7. Montar prompt com fontes.
8. Chamar ChatLLMProvider.
9. Validar resposta.
10. Converter citation_source_ids em fontes persistíveis.
11. Criar ChatMessage role=user.
12. Criar ChatMessage role=assistant.
13. Commit.
14. Retornar assistant message.
```

---

## 15.3. Tratamento de erro

Se o LLM falhar:

```json
{
  "answer": "Não foi possível gerar resposta agora. Tente novamente em alguns instantes.",
  "confidence": "low",
  "citations": [],
  "suggested_actions": [],
  "warnings": ["Falha no provedor LLM"]
}
```

Se não houver fontes e grounding for obrigatório:

```json
{
  "answer": "Não encontrei evidência suficiente na base indexada para responder com segurança.",
  "confidence": "low",
  "citations": [],
  "suggested_actions": [],
  "warnings": ["Sem fontes suficientes"]
}
```

---

# 16. API

Criar:

```text
backend/app/api/chat.py
```

Registrar em:

```text
backend/app/api/router.py
```

As rotas finais devem ser:

```text
/api/v1/chat
```

---

## 16.1. Endpoints obrigatórios

### 16.1.1. Health do chat

```http
GET /api/v1/chat/health
```

Resposta:

```json
{
  "enabled": true,
  "require_grounding": true,
  "provider": "existing-llm"
}
```

---

### 16.1.2. Criar conversa

```http
POST /api/v1/chat/conversations
```

Payload:

```json
{
  "title": "Análise do TR",
  "document_id": 1,
  "analysis_id": 2,
  "context": {
    "page": "analysis",
    "item_number": "4.3"
  }
}
```

Resposta: `201`

---

### 16.1.3. Listar conversas

```http
GET /api/v1/chat/conversations?page=1&page_size=20
```

Critérios:

1. Paginação simples.
2. Ordenar por `updated_at` descendente.
3. Retornar lista.
4. Não quebrar frontend.

---

### 16.1.4. Listar mensagens

```http
GET /api/v1/chat/conversations/{conversation_id}/messages
```

Critérios:

1. Retornar mensagens em ordem crescente de `created_at`.
2. Incluir citações.
3. Retornar 404 se conversa inexistente.

---

### 16.1.5. Enviar mensagem

```http
POST /api/v1/chat/conversations/{conversation_id}/messages
```

Payload:

```json
{
  "message": "Por que essa correção foi sugerida?"
}
```

Resposta: `ChatMessageResponse` do assistente.

---

### 16.1.6. Feedback

```http
POST /api/v1/chat/messages/{message_id}/feedback
```

Payload:

```json
{
  "feedback": "up"
}
```

Critérios:

1. Somente mensagens `assistant` recebem feedback.
2. Mensagem `user` retorna 400.
3. Mensagem inexistente retorna 404.
4. Feedback inválido retorna 422.

---

# 17. Banco de dados / init.sql

Arquivo:

```text
db/init.sql
```

Adicionar as tabelas de chat.

---

## 17.1. SQL sugerido

```sql
CREATE TABLE IF NOT EXISTS chat_conversations (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL DEFAULT 'Conversa LicitAI',
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE SET NULL,
    context_json JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSON NOT NULL DEFAULT '[]',
    suggested_actions JSON NOT NULL DEFAULT '[]',
    grounded BOOLEAN NOT NULL DEFAULT FALSE,
    confidence VARCHAR(20),
    provider VARCHAR(100),
    latency_ms INTEGER,
    feedback VARCHAR(10) CHECK (feedback IN ('up', 'down')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id
    ON chat_messages (conversation_id);
```

---

## 17.2. Migração opcional

Criar:

```text
db/migrations/20260806_add_chat.sql
```

Com o mesmo conteúdo idempotente.

---

## 17.3. Critérios

1. O `init.sql` continua válido para PostgreSQL.
2. Os testes `test_init_sql.py` continuam passando.
3. Se o teste tiver contrato rígido de tabelas, atualizar o teste para reconhecer as novas tabelas.
4. Nenhuma tabela existente é alterada.
5. Nenhuma coluna existente é modificada.
6. Nenhum índice existente é removido.

---

# 18. Frontend

---

## 18.1. Tipos

Arquivo:

```text
frontend/src/types/index.ts
```

Adicionar:

```ts
export interface ChatCitation {
  source_id: string;
  type: string;
  title?: string | null;
  excerpt: string;
  law_number?: string | null;
  article?: string | null;
  item_number?: string | null;
  document_id?: number | null;
  analysis_id?: number | null;
  correction_id?: number | null;
}

export interface ChatSuggestedAction {
  type: string;
  label: string;
  target?: string | null;
}

export interface ChatConversation {
  id: number;
  title: string;
  document_id?: number | null;
  analysis_id?: number | null;
  context_json?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  grounded: boolean;
  confidence?: "low" | "medium" | "high" | null;
  citations: ChatCitation[];
  suggested_actions: ChatSuggestedAction[];
  provider?: string | null;
  latency_ms?: number | null;
  feedback?: "up" | "down" | null;
  created_at: string;
}
```

---

## 18.2. API client

Arquivo:

```text
frontend/src/lib/api.ts
```

Adicionar funções usando o padrão existente.

Caminhos:

```ts
/chat/conversations
/chat/conversations/{id}/messages
/chat/messages/{message_id}/feedback
/chat/health
```

Como o router principal já usa `/api/v1`, o cliente deve chamar:

```ts
/chat/conversations
```

se o helper já prefixar `/api/v1`, ou:

```ts
/api/v1/chat/conversations
```

se o helper não prefixar automaticamente.

---

## 18.3. Componentes

Criar:

```text
frontend/src/components/chat/ChatPanel.tsx
frontend/src/components/chat/ChatMessage.tsx
frontend/src/components/chat/ChatInput.tsx
frontend/src/components/chat/CitationList.tsx
frontend/src/hooks/useChat.ts
```

---

## 18.4. Requisitos de UI

1. Painel lateral ou drawer.
2. Tema escuro premium.
3. Glassmorphism consistente com o projeto.
4. Badges para:
   - grounded;
   - confidence;
   - provider;
   - latency.
5. Citações em acordeão.
6. Botões de feedback up/down.
7. Estado de loading.
8. Estado de erro amigável.
9. Desabilitar envio enquanto estiver processando.
10. Não adicionar biblioteca nova de UI.

---

## 18.5. Integração principal

Integrar o painel na página:

```text
frontend/src/app/analysis/[id]/page.tsx
```

O painel deve receber:

```ts
documentId
analysisId
```

Contexto sugerido:

```json
{
  "page": "analysis",
  "analysis_id": 123,
  "document_id": 456
}
```

Se houver item selecionado na tela, incluir:

```json
{
  "item_number": "4.3"
}
```

---

## 18.6. Critérios de aceite do frontend

1. `npm run build` passa sem erro.
2. Nenhum type error.
3. A página de análise continua funcionando.
4. O chat abre e fecha sem quebrar layout.
5. Mensagens aparecem em ordem.
6. Citações aparecem.
7. Feedback funciona.
8. Sem fonte, a resposta mostra aviso de baixa evidência.
9. Não chamar backend fora do proxy.
10. Não usar URL hardcoded se o helper já usa proxy.

---

# 19. Testes obrigatórios

---

## 19.1. Arquivos

Criar:

```text
backend/tests/test_chat_validator.py
backend/tests/test_chat_api.py
```

---

## 19.2. Regras

1. Nenhum teste pode chamar Gemini real.
2. Nenhum teste pode chamar Groq real.
3. Nenhum teste pode chamar Ollama real.
4. Nenhum teste pode depender de `.env`.
5. Usar fake provider.
6. Usar banco SQLite em memória ou fixture existente.
7. Não adicionar teste E2E dependente de LLM real.

---

## 19.3. Testes do validador

```python
from app.services.chat.validator import validate_llm_answer


def test_validator_recusa_sem_fonte():
    raw = '{"answer": "Qualquer coisa", "confidence": "high", "citations": []}'

    result = validate_llm_answer(raw, set(), require_grounding=True)

    assert result.grounded is False
    assert "Não encontrei evidência suficiente" in result.answer


def test_validator_aceita_fonte_valida():
    raw = """
    {
      "answer": "Resposta baseada na fonte.",
      "confidence": "high",
      "citations": [
        {
          "source_id": "legal:1",
          "excerpt": "Art. 1"
        }
      ]
    }
    """

    result = validate_llm_answer(raw, {"legal:1"}, require_grounding=True)

    assert result.grounded is True
    assert result.citation_source_ids == ["legal:1"]


def test_validator_remove_citacao_invalida():
    raw = """
    {
      "answer": "Resposta.",
      "confidence": "medium",
      "citations": [
        {
          "source_id": "legal:999",
          "excerpt": "Fonte inexistente"
        }
      ]
    }
    """

    result = validate_llm_answer(raw, {"legal:1"}, require_grounding=True)

    assert result.grounded is False
    assert result.citation_source_ids == []


def test_validator_json_invalido():
    raw = "Isso não é JSON"

    result = validate_llm_answer(raw, {"legal:1"}, require_grounding=True)

    assert result.grounded is False
    assert "Não encontrei evidência suficiente" in result.answer


def test_validator_normaliza_confianca():
    raw = """
    {
      "answer": "Resposta.",
      "confidence": "errado",
      "citations": [
        {
          "source_id": "legal:1"
        }
      ]
    }
    """

    result = validate_llm_answer(raw, {"legal:1"}, require_grounding=True)

    assert result.confidence == "medium"
```

---

## 19.4. Testes de API

Testes mínimos:

1. `GET /api/v1/chat/health` retorna 200.
2. `POST /api/v1/chat/conversations` cria conversa.
3. `POST /api/v1/chat/conversations/{id}/messages` retorna resposta assistant fake.
4. Mensagem vazia retorna 422.
5. Mensagem longa retorna 422.
6. Conversa inexistente retorna 404.
7. `GET /api/v1/chat/conversations/{id}/messages` retorna mensagens.
8. Feedback em mensagem assistant funciona.
9. Feedback em mensagem user retorna 400.
10. Com `chat_enabled=False`, endpoints retornam 503.

---

## 19.5. Estratégia de fake provider

Usar override da dependência do chat LLM.

Exemplo conceitual:

```python
from app.services.chat.llm_adapter import FakeChatLLM


app.dependency_overrides[get_chat_llm] = lambda: FakeChatLLM()
```

Ou monkeypatch equivalente.

---

# 20. Logging e segurança

---

## 20.1. Logging

Usar:

```python
import logging

logger = logging.getLogger(__name__)
```

Eventos recomendados:

```text
chat.conversation.created
chat.message.received
chat.sources.retrieved
chat.llm.requested
chat.llm.failed
chat.answer.refused
chat.feedback.received
```

---

## 20.2. Segurança

1. Não logar chaves.
2. Não logar prompts completos em nível INFO.
3. Não expor `.env`.
4. Validar tamanho de mensagem.
5. Escapar conteúdo no frontend.
6. Não executar ações de escrita em entidades de negócio.
7. Não aceitar `suggested_actions` executáveis no MVP.
8. Não permitir que o chat altere análise ou correção.

---

# 21. Tarefas executáveis

---

## T0 — Baseline

### Ações

Rodar testes atuais:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

### Critério

- 126 testes passando.

---

## T1 — Configurações

### Arquivo

```text
backend/app/config.py
```

### Ações

Adicionar configurações de chat.

### Critérios

- Nenhuma variável obrigatória.
- Defaults seguros.
- `chat_enabled=True`.
- `chat_force_fake_provider=False`.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\config.py
```

---

## T2 — Models

### Arquivos

```text
backend/app/models/chat.py
backend/app/models/__init__.py
```

### Ações

Criar `ChatConversation` e `ChatMessage`.

### Critérios

- Models importáveis.
- Tabelas novas.
- Nenhuma tabela existente alterada.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\models\chat.py
```

---

## T3 — Schemas

### Arquivo

```text
backend/app/schemas/chat.py
```

### Ações

Criar schemas Pydantic.

### Critérios

- Validação de mensagem.
- Validação de feedback.
- Response com citações.
- `from_attributes=True`.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\schemas\chat.py
```

---

## T4 — LLM adapter

### Arquivo

```text
backend/app/services/chat/llm_adapter.py
```

### Ações

Criar:

- `ChatLLMProvider`;
- `FakeChatLLM`;
- `ExistingChatLLM`;
- `get_chat_llm`.

### Critérios

- Provider fake disponível.
- Provider real usa `get_llm_provider()`.
- Providers existentes não são alterados.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\services\chat\llm_adapter.py
```

---

## T5 — Source builder

### Arquivo

```text
backend/app/services/chat/sources.py
```

### Ações

Implementar fontes:

- legal;
- analysis;
- correction;
- document_item.

### Critérios

- Usa RAG existente.
- Não usa lazy loading perigoso.
- Falha de fonte não derruba o chat.
- Fontes têm `source_id`.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\services\chat\sources.py
```

---

## T6 — Prompt builder

### Arquivo

```text
backend/app/services/chat/prompts.py
```

### Ações

Implementar system prompt e user prompt.

### Critérios

- Exige JSON.
- Inclui fontes.
- Proíbe invenção.
- Não vaza segredo.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\services\chat\prompts.py
```

---

## T7 — Validator

### Arquivo

```text
backend/app/services/chat/validator.py
```

### Ações

Implementar validação de resposta.

### Critérios

- JSON inválido vira recusa.
- Fonte inválida é descartada.
- Sem fonte válida vira recusa.
- Confiança é normalizada.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_chat_validator.py -q
```

---

## T8 — Chat service

### Arquivo

```text
backend/app/services/chat/service.py
```

### Ações

Implementar fluxo completo.

### Critérios

- Persiste mensagens.
- Registra latência.
- Registra provider.
- Registra fontes usadas.
- Trata erro de LLM.
- Trata ausência de fontes.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m py_compile app\services\chat\service.py
```

---

## T9 — API

### Arquivos

```text
backend/app/api/chat.py
backend/app/api/router.py
```

### Ações

Criar endpoints e registrar no router `/api/v1`.

### Critérios

- Rotas finais sob `/api/v1/chat`.
- Health funciona.
- Conversas funcionam.
- Mensagens funcionam.
- Feedback funciona.
- Erros retornam status corretos.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_chat_api.py -q
```

---

## T10 — Testes de backend

### Arquivos

```text
backend/tests/test_chat_validator.py
backend/tests/test_chat_api.py
```

### Critérios

- Nenhum provider real é usado.
- Testes passam sem `.env`.
- Testes cobrem validação e API.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_chat_validator.py tests\test_chat_api.py -q
```

---

## T11 — init.sql

### Arquivos

```text
db/init.sql
backend/tests/test_init_sql.py
```

### Ações

Adicionar tabelas de chat ao `init.sql`.

### Critérios

- SQL válido.
- Contrato existente preservado.
- Testes `pglast` passando.
- Se necessário, atualizar `test_init_sql.py`.

### Verificação

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_init_sql.py -v
```

---

## T12 — Frontend types/API

### Arquivos

```text
frontend/src/types/index.ts
frontend/src/lib/api.ts
```

### Ações

Adicionar types e funções de chat.

### Critérios

- Types coerentes com backend.
- Cliente usa proxy existente.
- Nenhuma URL hardcoded desnecessária.

### Verificação

```powershell
cd frontend
npm run build
```

---

## T13 — Frontend components

### Arquivos

```text
frontend/src/components/chat/ChatPanel.tsx
frontend/src/components/chat/ChatMessage.tsx
frontend/src/components/chat/ChatInput.tsx
frontend/src/components/chat/CitationList.tsx
frontend/src/hooks/useChat.ts
```

### Critérios

- Componentes reutilizáveis.
- UI compatível com Tailwind.
- Loading e erro tratados.
- Citações exibidas.
- Feedback funcional.

### Verificação

```powershell
cd frontend
npm run build
```

---

## T14 — Integração na análise

### Arquivo

```text
frontend/src/app/analysis/[id]/page.tsx
```

### Ações

Adicionar botão/painel do Copiloto.

### Critérios

- Página continua funcionando.
- Chat recebe `documentId` e `analysisId`.
- Contexto é enviado na criação da conversa.
- Build passa.

### Verificação

```powershell
cd frontend
npm run build
```

---

## T15 — Logging, segurança e revisão

### Ações

Revisar:

- logs;
- validações;
- erros;
- secrets;
- rate limit;
- timeout;
- mensagens de erro.

### Critérios

- Nenhum segredo em log.
- Erros não vazam stacktrace cru para o usuário.
- Chat desabilitado retorna 503.
- Falha de LLM retorna resposta segura.

---

## T16 — Validação final

### Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pytest tests\test_chat_validator.py tests\test_chat_api.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_init_sql.py -v
```

### Frontend

```powershell
cd frontend
npm run build
```

### Manual smoke

Backend:

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

Verificar:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/chat/health
http://localhost:3000
```

---

# 22. Critérios de aceite finais

## Produto

- [ ] Usuário consegue abrir o Copiloto na análise.
- [ ] Usuário consegue criar conversa.
- [ ] Usuário consegue enviar pergunta.
- [ ] Usuário recebe resposta com citação ou recusa.
- [ ] Usuário consegue ver correções como fonte.
- [ ] Usuário consegue ver base legal como fonte.
- [ ] Usuário consegue dar feedback.
- [ ] Chat não altera dados de negócio.

---

## Técnico

- [ ] Endpoints sob `/api/v1/chat`.
- [ ] Models criados.
- [ ] Schemas criados.
- [ ] Chat service criado.
- [ ] Source builder criado.
- [ ] Validator criado.
- [ ] LLM adapter criado.
- [ ] Provider real existente reaproveitado.
- [ ] Fake provider usado em testes.
- [ ] RAG existente reaproveitado.
- [ ] `db/init.sql` atualizado.
- [ ] `test_init_sql.py` passando.
- [ ] Testes unitários passando.
- [ ] Nenhum teste novo depende de LLM real.
- [ ] Build do frontend passando.
- [ ] Logging sem secrets.
- [ ] Rate limit existente respeitado.
- [ ] Timeout existente respeitado.
- [ ] Nenhuma dependência nova adicionada.
- [ ] Nenhuma rota existente quebrada.

---

# 23. Métricas de sucesso

## Qualidade

| Métrica | Meta inicial |
|---|---:|
| Respostas factuais com citação válida | >= 90% |
| Recusa correta quando sem fonte | >= 90% |
| JSON inválido do modelo tratado | 100% |
| Testes unitários do chat passando | 100% |

---

## Produto

| Métrica | Meta inicial |
|---|---|
| Usuário consegue obter explicação com fonte | sim |
| Usuário consegue enviar feedback | sim |
| Chat não degrada análise | sim |
| Chat não aumenta E2E flaky | sim |

---

# 24. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| LLM real em testes | Flakiness | Fake provider obrigatório |
| Cota free tier esgotada | Falha de resposta | Failover existente + resposta segura |
| `.env` relativo ao CWD | Config errada | Documentar execução e usar defaults seguros |
| Lazy loading async | MissingGreenlet | Queries explícitas e `selectinload` |
| `init.sql` validado por pglast | Quebra de teste | Rodar `test_init_sql.py` |
| Frontend com proxy | Chamada errada | Usar `api.ts` e caminhos `/api/v1` |
| SQLite existente | Tabela ausente | Criar apenas tabelas novas |
| Alucinação | Alto | Grounding + validação + recusa |
| Chat parecer oráculo | Médio | UI mostra fontes, confiança e warnings |
| Crescimento de conversas | Médio | MVP persiste; futura política de retenção |

---

# 25. Definition of Done

O trabalho só está completo se:

- [ ] Backend implementado.
- [ ] Frontend implementado.
- [ ] Testes unitários passando.
- [ ] Testes de schema passando.
- [ ] Build do frontend passando.
- [ ] `init.sql` atualizado.
- [ ] Nenhuma dependência nova adicionada.
- [ ] Nenhuma ação de escrita em negócio executada pelo chat.
- [ ] Respostas sem fonte são recusadas quando grounding é obrigatório.
- [ ] Auditoria persistida.
- [ ] Logging sem secrets.
- [ ] `memory.md` atualizado.
- [ ] `README.md` atualizado se necessário.
- [ ] Não houver regressão nos 126 testes unitários.
- [ ] Não houver aumento de testes E2E dependentes de LLM real.

---

# 26. Atualização de memória recomendada

Após implementar, atualizar `memory.md` com algo como:

```text
Copiloto LicitAI (MVP consultivo) implementado:
- Chat assistivo em /api/v1/chat.
- Conversas e mensagens persistidas em chat_conversations e chat_messages.
- Respostas grounded com citações ou recusa.
- Integração com RAG jurídico, Analysis, Correction e DocumentItem.
- Provider LLM real reaproveitado via adapter; fake provider apenas para testes.
- Frontend integrado na página de análise.
- Nenhum teste unitário depende de LLM real.
```

---

# 27. Prompt canônico para IA executora

```text
Você é um engenheiro de software sênior executor. Sua missão é implementar o PRD "Copiloto LicitAI v1.1".

Regras obrigatórias:
1. Não quebre os 126 testes unitários existentes.
2. Não adicione dependências novas sem justificativa.
3. Não altere database.py nem get_db().
4. Não altere providers LLM existentes.
5. Não altere o RAG existente.
6. Não implemente ações de escrita em dados de negócio.
7. O chatbot do MVP é somente leitura e consultivo.
8. Toda resposta factual deve ter citação válida ou recusa explícita.
9. Testes unitários do chat devem usar fake provider.
10. Não crie testes E2E dependentes de LLM real.
11. Use rotas sob /api/v1.
12. Use o proxy existente do frontend.
13. Respeite logging JSON, rate limit e timeout existentes.
14. Execute as tarefas na ordem T0 até T16.
15. Após cada tarefa, rode a verificação correspondente.
16. Se um teste existente quebrar, pare e explique antes de continuar.
17. Ao final, rode a suíte completa do backend e o build do frontend.
18. Produza relatório final com arquivos alterados, testes adicionados, limitações e próximos passos.

Comece pela tarefa T0.
```

---

# 28. Recomendação final

Este PRD revisado transforma o Copiloto em uma feature:

- **alinhada ao projeto atual**;
- **segura**;
- **auditável**;
- **testável sem LLM real**;
- **integrada ao RAG existente**;
- **integrada ao provider LLM existente**;
- **compatível com SQLite nativo e PostgreSQL opcional**;
- **compatível com o frontend Next.js atual**;
- **sem impacto nas rotas existentes**;
- **sem aumentar a fragilidade dos testes E2E**.

A recomendação é executar exatamente esta versão, **v1.1**, em vez do PRD genérico anterior.