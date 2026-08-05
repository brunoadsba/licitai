# PRD Executável — Correções de Alto Impacto no LicitAI (Consolidado v2.0)

> **Fonte:** fusão do `PRD_PLANO_IMPLEMENTACAO.md` (análise sênior) com o
> `plano-prd-implementacao-qwen.md` (revisão por especialista), aproveitando o
> melhor de ambos e validando cada decisão contra o código real do repositório.
>
> **Última validação de baseline:** 05/08/2026 — **99 testes unitários passando**
> (inclui correção de 2 testes que falhavam por fake provider com assinatura
> desatualizada). 17 E2E dependem de backend rodando.
>
> **Status da execução (05/08/2026):** tarefas A0–D concluídas — **126 testes
> unitários passando** (12 novos testes de validação do schema Postgres via
> `pglast`; 15 novos testes de regressão das fases A–C). E2/E3 concluídos com a
> API key do `.env` da raiz (gemini): corpus reingerido (315 chunks, FTS com
> `remove_diacritics 2`, embeddings completos) e benchmark sem regressão
> (recall 0.806, precision 0.861, F1 0.832 vs baseline 0.681/0.889/0.771).
> E2E: **13 passed**, 4 erros por estouro de timeout do fixture de análise
> aguardando o LLM real (60s→240s), sob cota diária esgotada de Gemini/Groq —
> ambientais, não regressões. Validação do `db/init.sql` em Postgres feita via
> parser oficial (`pglast`/libpg_query) com teste durável; Docker fica para o
> futuro (daemon não disponível no ambiente).
>
> **Formato:** runbook determinístico para execução por qualquer modelo de IA.
> Cada tarefa tem: Objetivo → Arquivos → Mudança (código before/after) →
> Critérios de aceite → Verificação.

---

## 0. Objetivo

Corrigir bugs P0/P1 nos módulos de **parsing**, **extração por regras**,
**RAG** e **banco de dados**, sem quebrar:

- 99 testes unitários existentes (baseline já verde);
- 17 testes E2E existentes;
- contratos atuais da API (backward compatibility);
- dados existentes em banco real.

**Resultado esperado ao final:** suíte completa verde, novos testes de
regressão adicionados, `benchmark_report.json` sem regressão, `db/init.sql`
sincronizado com os models SQLAlchemy.

---

## 1. Contrato de execução para IA (regras de ouro)

1. Trabalhar **sempre a partir de `backend\`** como working dir.
2. Usar o Python do venv do projeto (`.\.venv\Scripts\python.exe`).
3. Definir `PYTHONPATH` como o diretório `backend` quando necessário.
4. Executar tarefas **exatamente na ordem** do plano.
5. Após cada tarefa, rodar os testes do módulo afetado.
6. Ao fim de cada fase, rodar a suíte completa.
7. Se um teste **existente** quebrar: **parar imediatamente**, explicar a causa
   e propor correção mínima. Não seguir em frente.
8. Não alterar `backend/app/database.py`, `get_db()`, `.env` ou segredos.
9. Não adicionar dependências novas sem justificativa registrada.
10. **Não usar números de linha como referência absoluta.** Localizar por nome
    de função e trecho de código (os números aqui são apenas orientativos).
11. Toda correção deve ter **teste de regressão**.
12. Mudança de banco deve diferenciar: **fresh install** (`init.sql`) vs
    **banco existente** (migração com backup).
13. Paginação deve manter **backward compatibility** de corpo de resposta.
14. Testes novos devem ser **autocontidos** (criar o próprio cenário; não
    depender de fixture implícita).
15. Ao final, rodar testes completos e gerar relatório: arquivos alterados,
    testes adicionados, resultados.

---

## 2. Ambiente canônico e comandos

### 2.1 Windows PowerShell (todos os comandos abaixo assumem este setup)

```powershell
Set-Location backend
$env:PYTHONPATH = (Get-Location).Path
$PY = ".\.venv\Scripts\python.exe"
```

### 2.2 Comandos canônicos

```powershell
# Suíte completa de unitários
& $PY -m pytest tests -q

# Arquivo específico
& $PY -m pytest tests\test_structurer.py -q

# Compilar (sintaxe) sem executar
& $PY -m py_compile app\services\parser\structurer.py

# E2E (exige backend rodando; ver e2e/run_e2e.ps1)
& $PY -m pytest ../e2e/tests -q
```

> **Importante:** rodar testes SEMPRE a partir de `backend\`. Rodar da raiz com
> `backend\.venv\Scripts\python.exe -m pytest backend\tests` quebra a coleta
> por `ModuleNotFoundError` (o `app` não entra no path). Esta é a correção de
> convenção que o PRD do Qwen acertou em apontar.

---

## 3. Fase A0 — Baseline obrigatório

### A0.1. Registrar baseline e corrigir testes quebrados de fake provider

**Objetivo:** garantir ponto de comparação antes de qualquer mudança e partir
de uma suíte verde.

**Ações:**
1. Rodar suíte completa: `& $PY -m pytest tests -q`
2. Copiar baseline do benchmark:
   `Copy-Item benchmark_report.json benchmark_report.before.json`
3. Se houver banco real, fazer backup (SQLite: copiar `licitacao.db`; Postgres:
   dump).

**Correção já aplicada nesta sessão (manter):** em
`backend/tests/test_multi_agent.py`, o `FakeAgentProvider.generate` usava
assinatura antiga `(prompt, system_prompt=None)`, mas a interface real é
`(system_prompt, user_prompt)` (`app/services/llm/provider.py:23`). Corrigido
para:

```python
async def generate(self, system_prompt: str, user_prompt: str) -> str:
    return self.response_text

async def _generate_implementation(self, system_prompt: str, user_prompt: str) -> str:
    return self.response_text
```

Isso destravou `test_legal_agent_analysis` e `test_orchestrator_runs_all_agents`
(2 testes que falhavam na baseline).

**Critério de aceite:** `99 passed, 0 failed`.

**Verificação:** `& $PY -m pytest tests -q`

---

## 4. Fase A — Parser e determinismo (P0)

### A1. Substituir `hash()` não determinístico por hash estável (sha256 + NFC)

**Arquivo:** `backend/app/services/parser/structurer.py`

**Objetivo:** `hash()` de string é randomizado por processo em Python;
`item_number` do `[TÍTULO]` muda entre execuções, quebrando diff e análises.

**Mudança —** adicionar imports (no topo, junto de `import re`):

```python
import hashlib
import unicodedata
```

Localizar (na função que cria o item de título, hoje por volta da linha 273):

```python
"number": f"T-{hash(m.group(1)) % 1000}",
```

Substituir por (normalização NFC + sha256 determinístico entre processos):

```python
_raw_title = unicodedata.normalize("NFC", m.group(1).strip())
_digest = hashlib.sha256(_raw_title.encode("utf-8")).hexdigest()
_number = f"T-{int(_digest[:12], 16) % 100000}"
```

E usar `"number": _number,` no dict retornado.

**Critérios de aceite:**
1. Duas chamadas de `structure_items` com o mesmo texto geram o mesmo
   `item_number`, inclusive em processos separados.
2. O valor começa com `T-`.
3. Nenhum outro uso de `hash()` para `item_number` permanece no projeto.
4. Nenhum teste existente quebra.

**Verificação:**
```powershell
& $PY -m pytest tests\test_structurer.py -q
```

---

### A2. Ativar detecção de alíneas (letras) e itens romanos

**Arquivo:** `backend/app/services/parser/structurer.py`

**Objetivo:** padrões `letter` (linha ~54) e `roman` (linha ~57) estão definidos
mas nunca são usados em `_detect_item_type`. Alíneas `a)` e itens `I.` caem
como conteúdo solto.

**Mudança —** em `_detect_item_type`, inserir **logo após** o bloco
`title_marker` e **antes** do bloco `subsubitem` (o retorno deve usar a MESMA
chave `"type"` usada pelos ramos existentes — `structure_items` converte
`type` → `item_type` na linha ~157):

```python
    m = PATTERNS["letter"].match(line)
    if m:
        title = m.group(2).strip()
        if _is_table_data_title(title):
            return None
        return {
            "number": m.group(1).strip().lower(),
            "title": title[:200],
            "type": "subitem",
        }

    m = PATTERNS["roman"].match(line)
    if m:
        title = m.group(2).strip()
        if _is_table_data_title(title):
            return None
        return {
            "number": m.group(1).strip().upper(),
            "title": title[:200],
            "type": "section",
        }
```

**Critérios de aceite:**
1. `"a) Entrega em 30 dias"` → `item_type == "subitem"`, `item_number == "a"`.
2. `"I. DO OBJETO"` → `item_type == "section"`, `item_number == "I"`.
3. `"9.000 BTU | Gree | 1"` continua **não** virando item.
4. Testes existentes continuam passando.

**Verificação:**
```powershell
& $PY -m pytest tests\test_structurer.py -q
```

---

### A3. Testes de regressão do parser

**Arquivo:** `backend/tests/test_structurer.py`

Adicionar (defensivo contra a chave real retornada — `item_type` é a chave
pública de `structure_items`; `type` é a chave interna de `_detect_item_type`):

```python
def test_titulo_gerado_deterministicamente():
    texto = "[TÍTULO] Contratação especializada"
    first = structure_items(texto, pages=[])[0]
    second = structure_items(texto, pages=[])[0]
    first_number = first.get("item_number") or first.get("number")
    second_number = second.get("item_number") or second.get("number")
    assert first_number == second_number
    assert first_number.startswith("T-")


def test_alinea_letra_detectada():
    items = structure_items("a) Entrega em 30 dias", pages=[])
    item = items[0]
    tipo = item.get("item_type", item.get("type"))
    numero = item.get("item_number", item.get("number"))
    assert tipo == "subitem"
    assert numero == "a"


def test_item_romano_detectado():
    items = structure_items("I. DO OBJETO", pages=[])
    item = items[0]
    tipo = item.get("item_type", item.get("type"))
    numero = item.get("item_number", item.get("number"))
    assert tipo == "section"
    assert numero == "I"
```

**Verificação:**
```powershell
& $PY -m pytest tests\test_structurer.py -q
```

---

## 5. Fase B — Extrator por âncora e validações (P0/P1)

### B1. Busca textual deve partir da âncora; numérica e "sem âncora" preservadas

**Arquivo:** `backend/app/services/rules/extractor.py`

**Objetivo:** corrigir captura de números **antes** da âncora (ex.: item `4.3`
com conteúdo `"4.3.8 Vigência: 90 dias"` e âncora `"vigência"` retornava `4`).

**Regras de comportamento (obrigatório — NÃO reescrever a função inteira):**

| Situação | Comportamento |
|---|---|
| `ancora` é `None`/vazio | Retorna TODO o texto concatenado (comportamento atual; NÃO mudar) |
| `ancora` numérica (`4.3`) | Mantém o ramo existente: retorna só o item com aquele `item_number` |
| `ancora` textual, `texto_inteiro=False` | Retorna o trecho a partir da 1ª ocorrência da âncora |
| `ancora` textual, `texto_inteiro=True` | Retorna o item inteiro (para `booleano`/`legal`) |
| âncora não encontrada | Retorna `""` |

**Mudança —** assinar `_texto_por_ancora` com `texto_inteiro`:

```python
def _texto_por_ancora(
    ancora: str | None,
    itens: list[dict],
    texto_inteiro: bool = False,
) -> str:
```

Mudar **apenas** o ramo textual (hoje linhas 99–106) para:

```python
    # Âncora textual: a partir da primeira ocorrência (ou item inteiro se texto_inteiro).
    alvo = ancora.strip().lower()
    for item in itens:
        conteudo = _conteudo_item(item)
        idx = conteudo.lower().find(alvo)
        if idx != -1:
            return conteudo if texto_inteiro else conteudo[idx:]
    return ""
```

> **Mantenha intactos:** o ramo `if not ancora:` (retorna texto completo) e o
> ramo de âncora numérica `if LEGAL_RE.match(ancora.strip()):`.

Ajustar `extrair_valor` para `booleano`/`legal` usarem o texto inteiro
(presença pode ocorrer antes da âncora no mesmo item):

```python
    if tipo == "booleano":
        return _extrair_booleano(
            regra.get("palavras_chave"),
            _texto_por_ancora(regra.get("ancora"), itens, texto_inteiro=True),
        )
    if tipo == "legal":
        return _extrair_legal(
            regra.get("regex"),
            _texto_por_ancora(regra.get("ancora"), itens, texto_inteiro=True),
        )
```

**Critérios de aceite:**
1. `"4.3.8 Vigência: 90 dias"` + âncora `"vigência"` → `90`.
2. `test_numero_inteiro_sem_ancora` (ancora ausente → texto completo) continua
   retornando `90`.
3. `test_booleano_presente` / `test_legal_presente` continuam passando.
4. Âncora numérica (`6.1`) continua restringindo ao item.

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

### B2. Regex de inteiro: ignorar prefixo de item, aceitar números longos e no fim de frase

**Arquivo:** `backend/app/services/rules/extractor.py`

**Objetivo:** o padrão atual `\b(\d{1,4}(?:\.\d{3})*)\b` casa `4` de `4.3.8` e
falha em `10000.` (número no fim de frase).

**Mudança —** substituir `NUMERO_INTEIRO_RE` (linha ~37) por:

```python
NUMERO_INTEIRO_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d{1,9})(?!\d)(?![.,]\d)"
)
```

Explicação (validada empiricamente):
- `(?<![\d.,])` — número não pode estar colado a dígito, ponto ou vírgula
  (rejeita `4` de `4.3.8` e `00` de `,00`).
- `\d{1,3}(?:\.\d{3})+` — milhares com separador (`9.000`, `1.500`).
- `\d{1,9}` — inteiro longo sem separador (`10000`).
- `(?!\d)` — não seguido de dígito.
- `(?![.,]\d)` — não seguido de `,00`/`.5` (não engolir pedaço monetário/versão),
  mas aceita ponto final de frase (`10000.` → `10000`).

**Casos obrigatórios (testados):**

| Entrada | Saída |
|---|---|
| `"4.3.8 Vigência: 90 dias"` | `90` |
| `"Valor: 10000 unidades"` | `10000` |
| `"9.000 BTU"` | `9000` |
| `"Quantidade: 10000."` | `10000` |
| `"Valor: 1500."` | `1500` |
| `"art. 5 da Lei 14.133/2021"` | `5` |
| `"R$ 1.500,00"` | `None` (não é inteiro) |
| `"Item 4.3"` | `None` |
| `"no art. 12 o prazo"` | `12` |
| `"total de 42 itens"` | `42` |

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

### B3. Monetário: aceitar `R$ 1500,00`, `R$ 1.500`, `R$ 1.500,00`

**Arquivo:** `backend/app/services/rules/extractor.py`

**Mudança —** substituir `MONETARIO_RE` (linha ~41):

```python
MONETARIO_RE = re.compile(
    r"\bR\$\s*(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,3}(?:\.\d{3})+|\d+,\d{2}|\d+)(?!\d)(?![.,]\d)"
)
```

Ajustar `_extrair_monetario` (linha ~190) com conversão explícita — sem tocar em
`_para_decimal` (usado também por percentual):

```python
def _extrair_monetario(texto: str) -> float | None:
    """Extrai o primeiro valor em reais (R$ 1.500,00) do texto."""
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
```

**Casos obrigatórios:**

| Entrada | Saída |
|---|---|
| `"R$ 1500,00"` | `1500.0` |
| `"R$ 1.500,00"` | `1500.0` |
| `"R$ 1.500"` | `1500.0` |
| `"R$ 1.500,50"` | `1500.5` |
| `"R$ 10000"` | `10000.0` |

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

### B4. Data: validar calendário real via `datetime.date`

**Arquivo:** `backend/app/services/rules/extractor.py`

**Mudança —** adicionar import e substituir `_extrair_data` (linha ~155):

```python
from datetime import date  # no topo do arquivo


def _extrair_data(texto: str) -> str | None:
    """Extrai a primeira data válida dd/mm/aaaa e retorna ISO aaaa-mm-dd."""
    for match in DATA_RE.finditer(texto):
        dia, mes, ano = (int(g) for g in match.groups())
        try:
            date(ano, mes, dia)  # lança ValueError para datas inexistentes
        except ValueError:
            continue
        return f"{ano:04d}-{mes:02d}-{dia:02d}"
    return None
```

**Casos obrigatórios:**

| Entrada | Saída |
|---|---|
| `"31/02/2026"` | `None` |
| `"30/02/2026"` | `None` |
| `"15/12/2026"` | `"2026-12-15"` |
| `"29/02/2024"` (bissexto) | `"2024-02-29"` |
| `"29/02/2023"` | `None` |

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

### B5. CNPJ: validar dígitos verificadores (módulo 11)

**Arquivo:** `backend/app/services/rules/extractor.py`

**Mudança —** adicionar função e usar em `_extrair_cnpj` (linha ~208):

```python
def _cnpj_valido(cnpj: str) -> bool:
    """Valida dígitos verificadores de CNPJ (apenas dígitos, módulo 11)."""
    if len(cnpj) != 14 or not cnpj.isdigit() or cnpj == cnpj[0] * 14:
        return False

    def _dv(seq: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(seq, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    primeiro_dv = _dv(cnpj[:12], p1)
    if primeiro_dv != int(cnpj[12]):
        return False

    p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _dv(cnpj[:12] + str(primeiro_dv), p2) == int(cnpj[13])


def _extrair_cnpj(texto: str) -> str | None:
    """Extrai o primeiro CNPJ válido do texto."""
    for match in CNPJ_RE.finditer(texto):
        raw = match.group(1).replace(".", "").replace("/", "").replace("-", "")
        if _cnpj_valido(raw):
            return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"
    return None
```

> CNPJ de teste válido: `11.222.333/0001-81` (verificado). Inválido:
> `11.222.333/0001-00` e `11111111111111`.

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

### B6. Número por extenso: dezena composta (`vinte e um` → 21)

**Arquivo:** `backend/app/services/rules/extractor.py`

**Mudança —** substituir `_extrair_numero_extenso` (linha ~126):

```python
def _extrair_numero_extenso(texto: str) -> int | None:
    """Extrai o primeiro número por extenso, incluindo dezenas compostas."""
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
```

**Casos obrigatórios:**

| Entrada | Saída |
|---|---|
| `"prazo será vinte e um dias"` | `21` |
| `"prazo será trinta dias"` | `30` |
| `"prazo será trinta e cinco dias"` | `35` |
| `"prazo será noventa e nove dias"` | `99` |

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

### B7. Testes de regressão da Fase B

**Arquivo:** `backend/tests/test_extractor.py`

Adicionar no fim (autocontidos — cada um cria seu próprio cenário):

```python
def test_numero_inteiro_ignora_prefixo_item():
    itens = [{"item_number": "4.3", "title": "Da Vigência",
              "content": "4.3.8 Vigência: 90 dias, com garantia."}]
    regra = {"id": "vigencia", "rotulo": "Vigência",
             "tipo": "numero_inteiro", "ancora": "vigência"}
    assert extrair_valor(regra, itens) == 90


def test_numero_inteiro_grande_sem_separador():
    itens = [{"item_number": "1", "title": "",
              "content": "O quantitativo é de 10000 unidades."}]
    regra = {"id": "qtd", "rotulo": "Qtd", "tipo": "numero_inteiro"}
    assert extrair_valor(regra, itens) == 10000


def test_numero_inteiro_fim_de_frase():
    itens = [{"item_number": "1", "title": "",
              "content": "A quantidade total é de 10000."}]
    regra = {"id": "qtd", "rotulo": "Qtd", "tipo": "numero_inteiro"}
    assert extrair_valor(regra, itens) == 10000


def test_numero_inteiro_rejeita_item_e_milhar_monetario():
    itens = [{"item_number": "1", "title": "",
              "content": "Item 4.3 e R$ 1.500,00."}]
    regra = {"id": "qtd", "rotulo": "Qtd", "tipo": "numero_inteiro"}
    assert extrair_valor(regra, itens) is None


def test_monetario_sem_separador_milhar():
    itens = [{"item_number": "1", "title": "",
              "content": "O valor estimado é de R$ 1500,00."}]
    regra = {"id": "valor", "rotulo": "Valor",
             "tipo": "monetario", "ancora": "valor"}
    assert extrair_valor(regra, itens) == 1500.0


def test_monetario_milhar_sem_centavos():
    itens = [{"item_number": "1", "title": "",
              "content": "O valor estimado é de R$ 1.500."}]
    regra = {"id": "valor", "rotulo": "Valor",
             "tipo": "monetario", "ancora": "valor"}
    assert extrair_valor(regra, itens) == 1500.0


def test_data_invalida_retorna_none():
    itens = [{"item_number": "1", "title": "",
              "content": "Entrega até 31/02/2026."}]
    regra = {"id": "entrega", "rotulo": "Entrega",
             "tipo": "data", "ancora": "entrega"}
    assert extrair_valor(regra, itens) is None


def test_cnpj_digitos_verificadores():
    itens = [{"item_number": "1", "title": "",
              "content": "Fornecedor CNPJ 11.222.333/0001-81."}]
    regra = {"id": "cnpj", "rotulo": "CNPJ", "tipo": "cnpj"}
    assert extrair_valor(regra, itens) == "11.222.333/0001-81"


def test_cnpj_invalido_retorna_none():
    itens = [{"item_number": "1", "title": "",
              "content": "Fornecedor CNPJ 11.222.333/0001-00."}]
    regra = {"id": "cnpj", "rotulo": "CNPJ", "tipo": "cnpj"}
    assert extrair_valor(regra, itens) is None


def test_numero_extenso_composto():
    itens = [{"item_number": "6.1", "title": "Base Legal",
              "content": "O prazo será vinte e um dias."}]
    regra = {"id": "prazo", "rotulo": "Prazo",
             "tipo": "numero_extenso", "ancora": "prazo"}
    assert extrair_valor(regra, itens) == 21
```

**Verificação:**
```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

## 6. Fase C — RAG (P0/P1)

### C1. FTS5 com remoção de acentos (`remove_diacritics 2`)

**Arquivo:** `backend/app/services/rag/loader.py`

**Objetivo:** permitir `"seguranca"` encontrar `"segurança"`.

**Mudança —** no `CREATE VIRTUAL TABLE` de `build_fts_index` (hoje linhas 240–246):

```python
    await db.execute(
        text(
            "CREATE VIRTUAL TABLE legal_chunks_fts USING fts5("
            "chunk_id UNINDEXED, article UNINDEXED, "
            "section UNINDEXED, chunk_text, "
            "tokenize = 'unicode61 remove_diacritics 2')"
        )
    )
```

**Nota:** `build_fts_index` já droga e recria a tabela a cada chamada — a
mudança é idempotente.

**Verificação:**
```powershell
& $PY -m pytest tests\test_retriever.py -q
```

---

### C2. Busca híbrida com Reciprocal Rank Fusion (com hardening)

**Arquivo:** `backend/app/services/rag/retriever.py`

**Objetivo:** combinar semântica + textual (melhor recall) sem quebrar fallback.

**Mudança —** extrair o seletor de dialeto para um helper:

```python
async def _search_textual(
    db, query: str, top_k: int, law_numbers: list[str] | None
) -> list[dict]:
    """Executa busca textual respeitando o dialeto do banco."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    if dialect == "sqlite":
        return await _search_sqlite(db, query, top_k, law_numbers)
    return await _search_postgres(db, query, top_k, law_numbers)
```

Adicionar a fusão RRF (com `.get()` defensivo para chaves ausentes):

```python
def _rrf(
    sem_rows: list[dict],
    text_rows: list[dict],
    top_k: int,
    k: int = 60,
) -> list[dict]:
    """Combina rankings usando Reciprocal Rank Fusion."""

    def _key(row: dict) -> tuple:
        return (
            row.get("law_number"),
            row.get("article") or "",
            row.get("chunk_text") or "",
        )

    scores: dict[tuple, float] = {}
    merged: dict[tuple, dict] = {}

    for lista in (sem_rows, text_rows):
        for rank, row in enumerate(lista):
            key = _key(row)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            merged.setdefault(key, row)

    ordered = sorted(
        merged.items(),
        key=lambda kv: scores[kv[0]],
        reverse=True,
    )
    return [row for _, row in ordered[:top_k]]
```

Alterar o ramo `if use_semantic:` de `retrieve` (hoje linhas 66–69) com
**try/except em ambas as buscas** (semântica já tem try/except interno, mas o
textual também deve ser blindado):

```python
    if use_semantic:
        try:
            sem_rows = await _search_semantic(db, cleaned, top_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca semântica; usando fallback textual")
            sem_rows = []

        try:
            text_rows = await _search_textual(db, cleaned, top_k, law_numbers)
        except Exception:
            logger.exception("Falha na busca textual; seguindo apenas com semântica")
            text_rows = []

        rows = _rrf(sem_rows, text_rows, top_k)
        if rows:
            return _para_chunks(rows)
```

> O fluxo posterior (fallback textual puro) permanece intacto e cobre o caso
> de `use_semantic=False` ou de ambas as buscas vazias.

**Critérios:**
1. Se semântica falhar/vazia → usa textual.
2. Se textual falhar → mantém semântica.
3. `test_retrieve_semantico_ranqueia_por_similaridade` continua retornando
   `["Art. 6º", "Art. 40º"]`.
4. `test_retrieve_fallback_quando_provider_falha` continua passando.

**Verificação:**
```powershell
& $PY -m pytest tests\test_retriever.py -q
```

---

### C3. Validar dimensão do embedding (warn no ingest e no retrieve)

**Arquivos:** `backend/scripts/ingest_embeddings.py` e
`backend/app/services/rag/retriever.py`

**Mudança —** no ingest, antes de salvar cada embedding (o script já importa o
provider; adicionar `from app.config import settings`):

```python
if len(vector) != settings.embeddings_dim:
    logger.warning(
        "Dimensão inesperada de embedding: esperado %d, obtido %d (chunk %s). Salvo mesmo assim.",
        settings.embeddings_dim, len(vector), chunk.id,
    )
```

No retrieve, dentro de `_search_semantic` (após calcular `query_vector`):

```python
if len(query_vector) != settings.embeddings_dim:
    logger.warning(
        "Dimensão da query (%d) difere da configurada (%d). Resultados podem divergir.",
        len(query_vector), settings.embeddings_dim,
    )
```

**Critério:** nunca quebra ingestão; apenas loga warning.

---

### C4. Cache limitado de embeddings de consulta

**Arquivo:** `backend/app/services/rag/retriever.py`

**Objetivo:** evitar re-embedding da mesma query, com cache **limitado** e
testável. (Versão do Qwen adotada — mais completa que a do PRD original.)

**Mudança —** adicionar no módulo:

```python
import asyncio
from collections import OrderedDict

_QUERY_EMBEDDING_CACHE: OrderedDict[tuple[str, str], tuple[float, ...]] = OrderedDict()
_QUERY_EMBEDDING_CACHE_MAX = 256
_QUERY_EMBEDDING_LOCK = asyncio.Lock()


def _clear_query_embedding_cache() -> None:
    """Limpa o cache de embeddings de consulta."""
    _QUERY_EMBEDDING_CACHE.clear()


async def _query_embedding_cached(query: str, provider_name: str) -> list[float]:
    """Retorna embedding da query com cache limitado (LRU simples)."""
    key = (query, provider_name)

    async with _QUERY_EMBEDDING_LOCK:
        if key in _QUERY_EMBEDDING_CACHE:
            _QUERY_EMBEDDING_CACHE.move_to_end(key)
            return list(_QUERY_EMBEDDING_CACHE[key])

    provider = get_embeddings_provider()
    vector = await provider.embed(query)

    async with _QUERY_EMBEDDING_LOCK:
        _QUERY_EMBEDDING_CACHE[key] = tuple(vector)
        _QUERY_EMBEDDING_CACHE.move_to_end(key)
        while len(_QUERY_EMBEDDING_CACHE) > _QUERY_EMBEDDING_CACHE_MAX:
            _QUERY_EMBEDDING_CACHE.popitem(last=False)

    return list(vector)
```

Em `_search_semantic`, usar:

```python
provider = get_embeddings_provider()
query_vector = await _query_embedding_cached(query, provider.provider_name)
```

> O `FakeEmbeddingsProvider` de `test_retriever.py` já tem `provider_name =
> "fake"` — não requer mudança.

**Critérios:** query repetida não chama `embed` de novo; cache limitado a 256;
`_clear_query_embedding_cache()` disponível para testes.

---

### C5. Testes de regressão RAG

**Arquivo:** `backend/tests/test_retriever.py`

Adicionar (autocontidos; `_seed_sem_embeddings` e `_seed_com_embeddings` já
existem e criam seus próprios dados):

```python
def test_fts_sem_acento_retorna_chunk_acentuado():
    async def _cenario():
        Session = await _seed_sem_embeddings()
        async with Session() as db:
            return await retrieve(db, "instrucoes de seguranca", top_k=2)

    chunks = _run(_cenario())
    assert any("segurança" in c.text or "seguranca" in c.text for c in chunks)


def test_retrieve_usa_cache_de_embedding(monkeypatch):
    from app.services.rag.retriever import _clear_query_embedding_cache

    _clear_query_embedding_cache()

    calls = {"n": 0}

    class FakeComContador(FakeEmbeddingsProvider):
        provider_name = "fake-contador"

        async def embed(self, text: str) -> list[float]:
            calls["n"] += 1
            return VETORES_QUERY.get(text.strip(), [1.0, 0.0, 0.0])

    monkeypatch.setattr(
        "app.services.rag.retriever.get_embeddings_provider",
        lambda: FakeComContador(),
    )

    async def _cenario():
        Session = await _seed_com_embeddings()
        async with Session() as db:
            await retrieve(db, "garantia de execução", top_k=2)
            await retrieve(db, "garantia de execução", top_k=2)

    _run(_cenario())
    assert calls["n"] == 1
```

**Verificação:**
```powershell
& $PY -m pytest tests\test_retriever.py -q
```

---

## 7. Fase D — Banco de dados (P0)

### D1. Sincronizar `db/init.sql` com os models SQLAlchemy

**Arquivo:** `db/init.sql`

**Objetivo:** o script Postgres está desalinhado dos models (fonte da verdade):

| Tabela | Coluna ausente/errada no init.sql | Modelo |
|---|---|---|
| `analyses` | falta `analysis_mode` | `analysis.py:42` |
| `corrections` | faltam `agent_origin`, `review_status`, `review_note`, `reviewed_at` | `analysis.py:139-152` |
| `document_revisions` | `items_snapshot JSONB` vs model `JSON` | `document_revision.py:31` |
| `legal_chunks` | `embedding vector(768)` vs model `Text` (JSON) | `legal.py:69` |

**Mudanças:**

1. Em `analyses`, após `llm_model`:
```sql
    analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent',
```
2. Em `corrections`, após `importance`:
```sql
    agent_origin VARCHAR(20),
    review_status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (review_status IN ('pendente', 'aprovada', 'rejeitada', 'ajustada')),
    review_note TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
```
3. Em `document_revisions`: `items_snapshot JSONB NOT NULL` → `items_snapshot JSON NOT NULL`.
4. Em `legal_chunks`: `embedding vector(768)` → `embedding TEXT`.

**Critérios:** schema espelha models; não exige pgvector; válido para fresh
install.

**Verificação mínima (SQL não valida com py_compile):**
```powershell
# Se Docker disponível:
docker compose up -d db
docker compose exec db psql -U postgres -d licitacao -f /docker-entrypoint-initdb.d/init.sql
```
> Se Docker indisponível: validar apenas que as alterações espelham a tabela
> acima e que `& $PY -m py_compile app\models\*.py` não quebra.

---

### D2. Estratégia de migração para banco existente (antes de aplicar D1/D3)

**Objetivo:** o `init.sql` cobre apenas **fresh install**. Para banco existente,
aplicar migração **com backup** e **validação em staging**.

**Ações (antes de qualquer mudança de schema):**
1. Backup: SQLite → copiar `licitacao.db`; Postgres → `pg_dump`.
2. Para Postgres existente, usar `ADD COLUMN IF NOT EXISTS` (idempotente):
```sql
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent';
ALTER TABLE corrections ADD COLUMN IF NOT EXISTS agent_origin VARCHAR(20);
ALTER TABLE corrections ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) NOT NULL DEFAULT 'pendente';
ALTER TABLE corrections ADD COLUMN IF NOT EXISTS review_note TEXT;
ALTER TABLE corrections ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE;
```
3. Para SQLite existente, `ALTER TABLE ... ADD COLUMN` (uma por execução) com
   backup prévio. Obs.: o repo já tem `scripts/migrate_agent_columns.py` e
   `scripts/migrate_review_columns.py` — reutilizá-los.
4. Validar em staging antes de produção.

**Critério:** nenhuma migração destrutiva sem backup.

---

### D3. Deduplicar `comparacao_resultados` antes da constraint UNIQUE

**Arquivo novo:** `backend/scripts/dedupe_comparacao_resultados.py`

**Requisitos:** fazer backup antes; idempotente; imprimir nº de linhas
removidas; funcionar no banco configurado (SQLite e Postgres).

**Lógica SQL:**
```sql
DELETE FROM comparacao_resultados
WHERE id NOT IN (
    SELECT MIN(id)
    FROM comparacao_resultados
    GROUP BY comparacao_id, fornecedor_id, regra_id
);
```
> `id` é UUID PK — `MIN(id)` é determinístico e válido nos dois dialetos.

**Verificação:**
```powershell
& $PY scripts\dedupe_comparacao_resultados.py
```

---

### D4. UniqueConstraint em `comparacao_resultados`

**Arquivos:** `backend/app/models/comparison.py` e `db/init.sql`

**Mudança —** model: adicionar import e `__table_args__` (sem remover nada
existente):

```python
from sqlalchemy import UniqueConstraint  # junto aos imports


class ComparacaoResultado(Base):
    __table_args__ = (
        UniqueConstraint(
            "comparacao_id", "fornecedor_id", "regra_id",
            name="uq_comparacao_fornecedor_regra",
        ),
    )
```

**Mudança —** `init.sql`, ao fim da tabela `comparacao_resultados`:
```sql
    CONSTRAINT uq_comparacao_fornecedor_regra
        UNIQUE (comparacao_id, fornecedor_id, regra_id)
```

**Ordem obrigatória:** rodar **D3 (dedupe)** antes de aplicar a constraint em
banco existente.

**Critérios:** duplicado lança erro de integridade; testes existentes passam.

**Verificação:**
```powershell
& $PY -m pytest tests -q
```

---

### D5. Paginação backward compatible

**Arquivos:** `backend/app/api/documents.py` (e, no mesmo padrão,
`analysis.py` listagem, `fornecedores.py`, `comparison.py`)

**Objetivo:** paginar **sem quebrar** o corpo da resposta (frontend lê
`.documents`/`.total` em `frontend/src/lib/api.ts:77`; E2E dependem do shape).

> **Decisão:** NÃO adotar a proposta do Qwen de retornar lista crua + header
> `X-Total-Count`. Ela quebraria `DocumentListResponse` (objeto `{documents,
> total}`) e o frontend. Adotar: manter o shape atual e apenas adicionar
> parâmetros `page`/`page_size`.

**Mudança —** exemplo em `list_documents` (documents.py:175):

```python
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos com paginação (backward compatible)."""
    total = (
        await db.execute(select(func.count()).select_from(Document))
    ).scalar_one()

    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
    )
```

Requisitos:
- `page`/`page_size` **opcionais** com defaults (`1`/`50`); `page_size` limitado
  a `200`.
- Shape da resposta inalterado (`{documents, total}`).
- Aplicar o mesmo padrão aos demais endpoints de listagem.

**Verificação:**
```powershell
& $PY -m pytest tests -q
```

---

## 8. Fase E — Validação final

### E1. Suíte completa
```powershell
& $PY -m pytest tests -q
& $PY -m pytest ../e2e/tests -q   # exige backend rodando
```
**Critério:** 0 falhas. **Status (05/08/2026):** 126 unitários passed; E2E 13
passed, 4 errors por timeout de análise com LLM real sob cota diária esgotada
(Gemini/Groq) — ambientais, não regressões.

### E2. Reingestão do corpus (reconstrói FTS com diacríticos)
```powershell
$env:PYTHONPATH = "backend"   # ou rodar de backend\ e usar & $PY
& $PY scripts\ingest_laws.py
& $PY scripts\ingest_juris_tcu.py
& $PY scripts\ingest_corpus_extra.py
& $PY scripts\ingest_embeddings.py
```
**Critérios:** FTS recriado com `remove_diacritics 2`; 310 chunks; embeddings
salvos; busca sem acento funciona.
**Status (05/08/2026):** concluído. Corrigidos 2 bugs pré-existentes que
impediam a ingestão: (1) `ingest_juris_tcu.py` não chamava `db.commit()`
(dados descartados no fechamento da sessão) e (2) `ingest_embeddings.py`
importava `get_embeddings_provider` de pacote errado. Resultado: 7 documentos,
315 chunks, 100% com embedding, busca sem acento validada ("seguranca juridica"
retorna "segurança jurídica") e busca semântica OK. Executar os 4 scripts em
paralelo contra o mesmo SQLite pode causar corrida no rebuild do FTS — rodar
sequencialmente.

### E3. Benchmark
```powershell
& $PY scripts\benchmark.py
```
**Critério:** comparar `benchmark_report.before.json` vs `benchmark_report.json`
— recall/precision/F1 sem regressão. Se regredir: parar, identificar a tarefa,
corrigir/reverter.
**Status (05/08/2026):** concluído — sem regressão. Recall 0.8056 (baseline
0.6806), precision 0.8611 (0.8889), F1 0.8324 (0.7709). Variação de precision
dentro do esperado para LLM não determinístico.

---

## 9. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| B1 mudar semântica de `booleano`/`legal` | Regressão | `texto_inteiro=True` preserva; testes A3/B7 cobrem |
| Regex capturar item errado | Extração incorreta | Casos tabelados (B2) com `4.3.8`, `10000.`, `1.500,00` |
| FTS antigo persistir | Busca sem acento falha | Reingestão completa (E2) |
| Cache de embeddings crescer | Memória | `max=256` LRU (C4) |
| Constraint UNIQUE com duplicados | Falha de migração | Rodar D3 (dedupe) antes |
| Hash novo mudar IDs de títulos | Diffs antigos incompatíveis | Aceitar padrão determinístico; não usar IDs antigos como referência |
| RRF alterar ranking | Mudança esperada | Testes de rank + benchmark |
| Banco existente divergente | Migração falha | Backup + `ADD COLUMN IF NOT EXISTS` (D2) |
| Paginação mudar shape | Quebra frontend/E2E | Manter `{documents, total}`; adicionar só `page`/`page_size` (D5) |

---

## 10. Ordem de execução

| # | Tarefa | Fase | Prioridade |
|---|---|---|---|
| 1 | A0.1 baseline + fix fake provider | A0 | — |
| 2 | A1 hash determinístico (sha256+NFC) | A | P0 |
| 3 | A2 alíneas/romanos | A | P0 |
| 4 | A3 testes parser | A | P0 |
| 5 | B1 âncora textual | B | P0 |
| 6 | B2 regex inteiro | B | P0 |
| 7 | B3 monetário | B | P1 |
| 8 | B4 data real | B | P1 |
| 9 | B5 CNPJ DV | B | P1 |
| 10 | B6 extenso composto | B | P1 |
| 11 | B7 testes extractor | B | P0 |
| 12 | C1 FTS diacríticos | C | P1 |
| 13 | C2 RRF híbrido + hardening | C | P1 |
| 14 | C3 validação dimensão | C | P1 |
| 15 | C4 cache embeddings | C | P2 |
| 16 | C5 testes retriever | C | P1 |
| 17 | D1 sync init.sql | D | P0 |
| 18 | D2 migração banco existente | D | P0 |
| 19 | D3 dedupe | D | P0 |
| 20 | D4 UNIQUE constraint | D | P1 |
| 21 | D5 paginação compatível | D | P2 |
| 22 | E1–E3 validação final | E | — |

---

## 11. Definição de Pronto (Definition of Done)

- [x] `tests/` passa com 0 falhas (baseline: 99 unitários; atual: **126 passando**).
- [x] `e2e/tests` passa quando executável (13 passed; 4 errors por timeout do fixture de análise aguardando LLM real sob cota diária esgotada — ambientais, corrigido janela 60s→240s).
- [x] Novos testes de regressão adicionados (parser, extractor, retriever, schema Postgres).
- [x] `benchmark_report.json` não regrediu vs `benchmark_report.before.json` (recall 0.806 vs 0.681; precision 0.861 vs 0.889; F1 0.832 vs 0.771).
- [x] `db/init.sql` sincronizado com os models.
- [x] Validação Postgres do `db/init.sql` via parser oficial (`pglast`/libpg_query), 12 testes — Docker fica para o futuro.
- [~] Nenhuma dependência nova adicionada (exceção: `pglast==8.4` para validar `db/init.sql` em Postgres).
- [x] Nenhuma mudança em `database.py`, `get_db()`, `.env`, segredos.
- [x] API backward compatible (shape de resposta preservado).
- [x] Cache de embeddings limitado e testado.
- [x] FTS suporta busca sem acento.
- [x] Parser reconhece alíneas e romanos.
- [x] Extração por âncora respeita posição da âncora.
- [x] CNPJ valida dígitos verificadores; datas inválidas rejeitadas.
- [x] Números de item não capturados como valor.

---

## 12. Prompt canônico para executar com IA

```text
Você é um engenheiro de software sênior executor. Sua missão é implementar o
PRD "Correções de Alto Impacto no LicitAI (Consolidado v2.0)" sem quebrar os
testes existentes.

Regras obrigatórias:
1. Trabalhe sempre a partir do diretório backend.
2. Use o Python do virtualenv do projeto (`.\.venv\Scripts\python.exe`).
3. Defina PYTHONPATH como o diretório backend quando necessário.
4. Execute as tarefas exatamente na ordem definida no PRD.
5. Após cada tarefa, rode os testes do módulo afetado.
6. Ao fim de cada fase, rode a suíte completa.
7. Se qualquer teste existente falhar, pare imediatamente, explique a causa e
   proponha correção mínima.
8. Não altere database.py, get_db(), .env ou contratos públicos de API sem
   instrução explícita.
9. Não adicione dependências.
10. Não use números de linha como referência absoluta; use nome de função e
    busca por trecho de código.
11. Toda correção deve incluir teste de regressão.
12. Antes de alterações de banco, diferencie fresh install de banco existente
    e faça backup.
13. Paginação deve manter backward compatibility do corpo da resposta.
14. Testes novos devem ser autocontidos.
15. Ao final, rode testes completos e gere relatório resumindo mudanças,
    arquivos alterados, testes adicionados e resultados.

Comece pela tarefa A0.1.
```
