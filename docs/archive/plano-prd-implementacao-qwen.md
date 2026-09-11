# Análise Sênior de PRD — LicitAI

Como especialista sênior em PRD e execução assistida por IA: o seu plano já está **muito acima da média**. Ele tem objetivo claro, tarefas pequenas, arquivos afetados, critérios de aceite, comandos de verificação e preocupação com regressão. Isso é raro e bom.

Mas, para ser realmente executável por **qualquer modelo de IA** — sem contexto humano, sem “bom senso” implícito e sem conhecimento prévio do repositório — ele ainda precisa de ajustes importantes.

## Veredito executivo

**Nota atual do PRD: 8,2/10**  
**Nota potencial após revisão: 9,7/10**

O plano está bom para um engenheiro humano sênior, mas ainda não está totalmente “machine-executable” porque possui:

1. **Comandos ambíguos** e inconsistentes de ambiente.
2. **Referência frágil a números de linha**.
3. **Testes com suposições implícitas** sobre chaves de retorno.
4. **Cache de embeddings com definição incompleta**.
5. **Paginação com risco de quebrar contrato de API/E2E**.
6. **Mudança de banco sem migração explícita para ambientes existentes**.
7. **Verificações FTS insuficientes ou genéricas**.
8. **Regex com casos de borda não cobertos**.
9. **Dependência de fixtures/cenários não explicitados**.
10. **Falta de um contrato explícito de execução para IA**.

Abaixo faço primeiro a análise crítica e depois entrego uma versão revisada do PRD, mais robusta, determinística e pronta para execução por qualquer agente de código.

---

# 1. Pontos críticos encontrados no PRD original

## 1.1. Ambiente e comandos inconsistentes

O PRD diz:

> Working dir para backend: `backend\`

Mas depois usa comandos como:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests -q
```

Se o diretório de trabalho já é `backend`, o comando deveria ser:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Se o diretório é a raiz do repositório, então o caminho de testes deveria ser:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Do jeito está, uma IA pode executar no diretório errado e quebrar por `ModuleNotFoundError`, caminho de testes inexistente ou `PYTHONPATH` incorreto.

### Correção

Padronizar:

```powershell
Set-Location backend
$env:PYTHONPATH = (Get-Location).Path
$PY = ".\.venv\Scripts\python.exe"
& $PY -m pytest tests -q
```

Ou, para Linux/POSIX:

```bash
cd backend
export PYTHONPATH="$PWD"
PY=".venv/bin/python"
$PY -m pytest tests -q
```

---

## 1.2. Uso de números de linha é frágil

O PRD usa várias vezes:

> linha 273  
> linha 54  
> linha 83  
> linhas 99–106

Para uma IA executora, isso é perigoso porque:

- o arquivo pode já ter sido alterado;
- o modelo pode não conseguir localizar exatamente a linha;
- pequenos diffs mudam a numeração;
- ferramentas de edição podem interpretar linha 0/1 diferente.

### Correção

Sempre referenciar por:

- nome do arquivo;
- nome da função;
- padrão de busca;
- trecho de código antigo;
- trecho de código novo.

Exemplo:

> Em `backend/app/services/parser/structurer.py`, dentro da função `structure_items`, localize o trecho `"number": f"T-{hash(m.group(1)) % 1000}"` e substitua por...

Isso é muito mais executável.

---

## 1.3. A1: `hash()` por `md5()` resolve, mas pode melhorar

A proposta original:

```python
"number": f"T-{int(hashlib.md5(m.group(1).encode('utf-8')).hexdigest()[:8], 16) % 100000}",
```

Está funcional, mas tem três problemas:

1. MD5 não é necessário; SHA-256 é mais padronizado e evita preocupação com colisões, mesmo não sendo uso criptográfico.
2. Falta normalização Unicode. `Contratação` pode vir com diferentes representações de acento.
3. O teste proposto não valida determinismo entre processos de verdade.

### Correção recomendada

Usar:

```python
import hashlib
import unicodedata

raw = unicodedata.normalize("NFC", m.group(1).strip())
digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
number = f"T-{int(digest[:12], 16) % 100000}"
```

E adicionar teste explícito de estabilidade.

---

## 1.4. A2: ativação de alíneas e romanos está boa, mas falta compatibilidade de schema

A mudança interna propõe retornar:

```python
"type": "subitem"
```

Mas o teste usa:

```python
items[0]["item_type"]
```

Isso pode quebrar se `structure_items()` não converter `type` para `item_type`.

Para uma IA, essa inconsistência é fatal.

### Correção

Deixar explícito:

- `_detect_item_type()` deve seguir o mesmo formato dos ramos existentes.
- Os testes devem usar a chave pública retornada por `structure_items()`.
- Se o retorno público for `item_type`, testar `item_type`.
- Se for `type`, testar `type`.

Para tornar executável sem conhecimento prévio, recomendo teste defensivo:

```python
tipo = item.get("item_type", item.get("type"))
```

Mas o ideal é inspecionar o contrato real da função e escrever o teste contra esse contrato.

---

## 1.5. B1: mudança de âncora textual está correta, mas precisa preservar casos antigos

A ideia de retornar o texto **a partir da âncora** está correta. Porém, o PRD precisa deixar claro:

1. O que acontece quando `ancora` é `None`.
2. O que acontece quando a âncora é numérica.
3. O que acontece quando a âncora não é encontrada.
4. Que `booleano` e `legal` continuam usando texto inteiro.
5. Que a busca não deve retornar números anteriores à âncora.

Sem isso, uma IA pode reescrever a função inteira e quebrar âncora numérica.

### Correção

Especificar:

> Mantenha o ramo existente de âncora numérica intacto. Apenas altere o ramo de âncora textual para fatiar o conteúdo a partir da primeira ocorrência da âncora.

E adicionar casos de teste:

- âncora encontrada no meio do item;
- âncora não encontrada;
- âncora numérica;
- `booleano` com palavra antes da âncora;
- `legal` com presença antes da âncora.

---

## 1.6. B2: regex de número inteiro pode rejeitar número no fim de frase

A regex proposta:

```python
NUMERO_INTEIRO_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{3})+|\d{1,9})(?![\d.])")
```

Resolve o caso de `4.3.8`, mas cria um efeito colateral:

```text
O quantitativo é 10000.
```

O número `10000` pode não casar porque está seguido de ponto final.

### Correção recomendada

Usar lookahead que rejeite ponto **somente quando seguido de dígito**, não ponto final de frase.

```python
NUMERO_INTEIRO_RE = re.compile(
    r"(?<![\d.])(\d{1,3}(?:\.\d{3})+|\d{1,9})(?!\d)(?![.,]\d)"
)
```

Isso:

- aceita `10000.`;
- aceita `9.000`;
- rejeita `4` em `4.3.8`;
- rejeita `1.500` quando seguido de `,00` em contexto monetário;
- evita capturar pedaços de item/versão.

---

## 1.7. B3: monetário precisa de conversão explícita

A regex monetária está boa, mas o PRD precisa definir completamente a conversão.

Exemplo:

```text
R$ 1.500
```

Não pode virar `1.5`.

### Correção

No extrator monetário, definir:

```python
if "," in raw:
    raw = raw.replace(".", "").replace(",", ".")
else:
    raw = raw.replace(".", "")
return float(raw)
```

E não alterar `_para_decimal` globalmente sem verificar outros usos.

---

## 1.8. B4: validação de data deve usar `datetime.date`

A proposta com `calendar.monthrange` funciona, mas `datetime.date` é mais simples e legível.

### Correção

```python
from datetime import date

try:
    date(ano, mes, dia)
except ValueError:
    continue
```

Isso já trata:

- 31/02;
- 30/02;
- ano bissexto;
- mês inválido;
- ano zero.

---

## 1.9. C1: FTS com `remove_diacritics 2` está correto, mas falta teste autocontido

O teste proposto depende de fixtures específicas:

```python
assert any(c.article == "Art. 28º" for c in chunks)
```

Se o corpus de teste não tiver esse artigo, o teste falha por motivo errado.

### Correção

Criar teste autocontido:

- inserir chunk com `segurança`;
- buscar `seguranca`;
- esperar retorno do chunk.

---

## 1.10. C2: RRF está bem pensado, mas falta tratamento de erro

A fusão híbrida melhora recall, mas precisa definir:

1. O que acontece se `_search_textual` falhar.
2. O que acontece se `_search_semantic` retornar vazio.
3. Como desempatar scores iguais.
4. Quais campos são obrigatórios no row.
5. Se `law_number` ou `article` podem ser `None`.

### Correção

Adicionar:

```python
try:
    text_rows = await _search_textual(...)
except Exception:
    logger.exception("Falha na busca textual; seguindo apenas com semântica")
    text_rows = []
```

E usar `.get()` na chave do RRF.

---

## 1.11. C4: cache de embeddings está ambíguo e potencialmente ilimitado

O PRD oscila entre:

- `lru_cache`;
- função async;
- dicionário simples;
- `maxsize=256`.

Para execução por IA, isso precisa ser fechado.

### Correção

Implementar cache async simples, limitado e testável:

```python
_QUERY_EMBEDDING_CACHE: OrderedDict[tuple[str, str], tuple[float, ...]] = OrderedDict()
_QUERY_EMBEDDING_CACHE_MAX = 256
_QUERY_EMBEDDING_LOCK = asyncio.Lock()
```

E expor função:

```python
def _clear_query_embedding_cache() -> None:
    _QUERY_EMBEDDING_CACHE.clear()
```

Testes devem limpar o cache antes de executar.

---

## 1.12. D3: paginação pode quebrar frontend/E2E

O PRD propõe mudar a resposta para:

```python
DocumentListResponse(
    documents=...,
    total=...,
)
```

Se os testes E2E ou o frontend esperam uma lista, isso quebra.

Como o objetivo é **não quebrar os 17 E2E**, a paginação deve ser backward compatible.

### Correção

Implementar paginação mantendo corpo atual, e adicionar total via header:

```http
X-Total-Count: 123
```

Exemplo:

```python
response.headers["X-Total-Count"] = str(total)
return documents
```

Assim:

- clientes antigos continuam funcionando;
- frontend pode evoluir depois;
- E2E não quebra;
- API ganha paginação.

---

## 1.13. D1/D2: banco precisa de estratégia de migração

Alterar apenas `db/init.sql` resolve banco novo. Não resolve banco existente.

Para qualquer IA executar com segurança, é preciso diferenciar:

1. **Fresh install**: rodar `init.sql`.
2. **Banco existente**: aplicar migração com backup.
3. **SQLite existente**: limitações de `ALTER TABLE`.
4. **Postgres existente**: usar `ADD COLUMN IF NOT EXISTS`, `DO $$ ... $$`, etc.

### Correção

Adicionar tarefa explícita:

- criar script/migração para ambientes existentes;
- exigir backup antes;
- rodar dedupe antes da constraint;
- validar em staging antes de produção.

---

# 2. PRD revisado, executável e recomendado para IA

Abaixo segue a versão que eu considero mais robusta para execução autônoma.

---

# PRD Executável — Correções de Alto Impacto no LicitAI v2.0

## 0. Objetivo

Corrigir bugs P0/P1 nos módulos de parsing, extração por regras, RAG e banco de dados, sem quebrar:

- 99 testes unitários existentes;
- 17 testes E2E existentes;
- contratos atuais da API;
- dados existentes em banco real.

## 1. Resultado esperado

Ao final da execução:

1. Todos os testes existentes passam.
2. Novos testes de regressão passam.
3. `benchmark_report.json` não apresenta regressão em recall/precision/F1.
4. `db/init.sql` está sincronizado com models SQLAlchemy.
5. Nenhuma dependência nova foi adicionada sem justificativa.
6. Nenhuma mudança foi feita em:
   - `backend/app/database.py`;
   - `get_db()`;
   - `.env`;
   - segredos.

---

# 2. Contrato de execução para IA

A IA executora deve obedecer obrigatoriamente:

## 2.1. Ordem de execução

Executar as tarefas exatamente na ordem:

1. A0 — Baseline
2. A1 — Hash determinístico
3. A2 — Alíneas e romanos
4. A3 — Testes de parser
5. B1 — Âncora textual
6. B2 — Número inteiro
7. B3 — Monetário
8. B4 — Data válida
9. B5 — CNPJ com DV
10. B6 — Número por extenso composto
11. B7 — Testes de extração
12. C1 — FTS com diacríticos
13. C2 — RAG híbrido RRF
14. C3 — Validação de dimensão
15. C4 — Cache de embeddings
16. C5 — Testes RAG
17. D1 — Sincronizar init.sql
18. D4 — Deduplicar comparacao_resultados
19. D2 — Unique constraint
20. D3 — Paginação backward compatible
21. E1 — Suíte completa
22. E2 — Reingestão
23. E3 — Benchmark

## 2.2. Regras de ouro

1. Nunca alterar `backend/app/database.py`.
2. Nunca alterar `get_db()`.
3. Nunca commitar `.env`.
4. Nunca adicionar dependência nova.
5. Nunca usar números de linha como referência absoluta.
6. Sempre rodar a suíte completa após cada fase.
7. Se um teste existente quebrar, parar imediatamente.
8. Não mudar contrato de resposta da API sem necessidade explícita.
9. Não executar migração destrutiva em banco real sem backup.
10. Toda correção deve ter teste de regressão.

## 2.3. Ambiente canônico

### Windows PowerShell

```powershell
Set-Location backend
$env:PYTHONPATH = (Get-Location).Path
$PY = ".\.venv\Scripts\python.exe"
```

### Linux/macOS

```bash
cd backend
export PYTHONPATH="$PWD"
PY=".venv/bin/python"
```

## 2.4. Comandos canônicos

Rodar testes unitários:

```powershell
& $PY -m pytest tests -q
```

Rodar arquivo específico:

```powershell
& $PY -m pytest tests\test_structurer.py -q
```

Compilar arquivo:

```powershell
& $PY -m py_compile app\services\parser\structurer.py
```

Rodar E2E, se aplicável:

```powershell
& $PY -m pytest ../e2e/tests -q
```

---

# 3. Fase A0 — Baseline obrigatório

## A0.1. Backup e baseline

**Objetivo:** criar ponto de comparação antes das mudanças.

**Ações:**

1. Rodar todos os testes unitários.
2. Copiar `benchmark_report.json` atual para `benchmark_report.before.json`.
3. Se houver banco real, fazer backup do arquivo SQLite ou dump Postgres.

**Comandos:**

```powershell
& $PY -m pytest tests -q
Copy-Item benchmark_report.json benchmark_report.before.json -ErrorAction SilentlyContinue
```

**Critério de aceite:**

- Suíte atual passa antes das mudanças.
- Baseline salvo.

---

# 4. Fase A — Parser e determinismo

## A1. Substituir `hash()` por hash estável

**Arquivo:**

```text
backend/app/services/parser/structurer.py
```

**Objetivo:**

Eliminar `hash()` nativo para geração de `item_number` sintético, pois ele muda entre processos.

**Mudança:**

Adicionar imports:

```python
import hashlib
import unicodedata
```

Localizar, na função responsável por criar item de título sintético, o trecho:

```python
"number": f"T-{hash(m.group(1)) % 1000}",
```

Substituir por:

```python
_raw_title = unicodedata.normalize("NFC", m.group(1).strip())
_digest = hashlib.sha256(_raw_title.encode("utf-8")).hexdigest()
_number = f"T-{int(_digest[:12], 16) % 100000}"
```

E usar:

```python
"number": _number,
```

**Critérios de aceite:**

1. Duas chamadas com o mesmo texto geram o mesmo `item_number`.
2. O valor começa com `T-`.
3. Não existe uso de `hash()` para gerar `item_number`.
4. Nenhum teste existente quebra.

**Teste novo:**

```python
def test_titulo_gerado_deterministicamente():
    texto = "[TÍTULO] Contratação especializada"

    first = structure_items(texto, pages=[])[0]
    second = structure_items(texto, pages=[])[0]

    first_number = first.get("item_number") or first.get("number")
    second_number = second.get("item_number") or second.get("number")

    assert first_number == second_number
    assert first_number.startswith("T-")
```

**Verificação:**

```powershell
& $PY -m pytest tests\test_structurer.py -q
```

---

## A2. Ativar detecção de alíneas e itens romanos

**Arquivo:**

```text
backend/app/services/parser/structurer.py
```

**Objetivo:**

Ativar padrões `letter` e `roman`, hoje definidos mas não usados.

**Mudança:**

Na função `_detect_item_type`, após os verificadores de título/cláusula e antes de padrões numéricos/subsubitem, inserir:

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

**Atenção:**

- Se os ramos existentes de `_detect_item_type` retornarem outra chave em vez de `"type"`, usar exatamente a mesma chave dos ramos existentes.
- Não alterar a ordem dos padrões já existentes, exceto pela inserção desses dois blocos no ponto correto.

**Critérios de aceite:**

1. `"a) Entrega em 30 dias"` vira subitem.
2. `"I. DO OBJETO"` vira section.
3. Linha de tabela continua não virando item.
4. Testes existentes continuam passando.

**Verificação:**

```powershell
& $PY -m pytest tests\test_structurer.py -q
```

---

## A3. Testes de regressão do parser

**Arquivo:**

```text
backend/tests/test_structurer.py
```

Adicionar:

```python
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


def test_dados_de_tabela_nao_viram_itens_para_alinea_ou_romano():
    items = structure_items("9.000 BTU | Gree | 1", pages=[])
    assert not items or all(
        (item.get("item_type") or item.get("type")) != "section"
        for item in items
    )
```

**Verificação:**

```powershell
& $PY -m pytest tests\test_structurer.py -q
```

---

# 5. Fase B — Extrator por âncora e validações

## B1. Âncora textual deve buscar somente após a ocorrência da âncora

**Arquivo:**

```text
backend/app/services/rules/extractor.py
```

**Objetivo:**

Evitar que números anteriores à âncora sejam capturados.

**Mudança:**

Alterar `_texto_por_ancora` para aceitar `texto_inteiro`.

Assinatura:

```python
def _texto_por_ancora(
    ancora: str | None,
    itens: list[dict],
    texto_inteiro: bool = False,
) -> str:
```

Requisitos:

1. Se `ancora` for vazia ou `None`, retornar `""`.
2. Se existir lógica atual para âncora numérica, mantê-la intacta.
3. Para âncora textual:
   - se `texto_inteiro=True`, retornar conteúdo completo do item onde a âncora aparecer;
   - se `texto_inteiro=False`, retornar somente o trecho a partir da primeira ocorrência da âncora.

Implementação de referência para o ramo textual:

```python
    alvo = ancora.strip().lower()

    if texto_inteiro:
        for item in itens:
            conteudo = _conteudo_item(item)
            if alvo in conteudo.lower():
                return conteudo
        return ""

    for item in itens:
        conteudo = _conteudo_item(item)
        idx = conteudo.lower().find(alvo)
        if idx != -1:
            return conteudo[idx:]

    return ""
```

Ajustar `extrair_valor`:

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

1. Em `"4.3.8 Vigência: 90 dias"`, âncora `"vigência"` retorna `90`.
2. `booleano` continua funcionando se a palavra estiver antes da âncora.
3. `legal` continua funcionando se o padrão estiver antes da âncora.
4. Âncora não encontrada retorna valor vazio/None conforme tipo.
5. Testes existentes continuam passando.

**Verificação:**

```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

## B2. Número inteiro deve ignorar prefixos de item e aceitar números longos

**Arquivo:**

```text
backend/app/services/rules/extractor.py
```

**Objetivo:**

Corrigir captura errada de prefixos como `4` em `4.3.8`.

**Mudança:**

Substituir `NUMERO_INTEIRO_RE` por:

```python
NUMERO_INTEIRO_RE = re.compile(
    r"(?<![\d.])(\d{1,3}(?:\.\d{3})+|\d{1,9})(?!\d)(?![.,]\d)"
)
```

Ajustar `_extrair_numero`, se necessário:

```python
def _extrair_numero(texto: str) -> int | None:
    """Extrai o primeiro número inteiro relevante do texto."""
    for match in NUMERO_INTEIRO_RE.finditer(texto):
        raw = match.group(1).replace(".", "")
        try:
            return int(raw)
        except ValueError:
            continue
    return None
```

**Casos obrigatórios:**

| Entrada | Saída esperada |
|---|---:|
| `"4.3.8 Vigência: 90 dias"` | `90` |
| `"Valor: 10000 unidades"` | `10000` |
| `"9.000 BTU"` | `9000` |
| `"Quantidade: 10000."` | `10000` |
| `"Item 4.3"` | não capturar `4` nem `3` como inteiro isolado |

**Verificação:**

```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

## B3. Monetário deve aceitar `R$ 1500,00` e `R$ 1.500`

**Arquivo:**

```text
backend/app/services/rules/extractor.py
```

**Mudança:**

Substituir `MONETARIO_RE` por:

```python
MONETARIO_RE = re.compile(
    r"\bR\$\s*(\d{1,3}(?:\.\d{3})+,\d{2}|\d{1,3}(?:\.\d{3})+|\d+,\d{2}|\d+)(?!\d)(?![.,]\d)"
)
```

Implementar ou ajustar `_extrair_monetario`:

```python
def _extrair_monetario(texto: str) -> float | None:
    """Extrai o primeiro valor em reais do texto."""
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
|---|---:|
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

## B4. Data deve validar calendário real

**Arquivo:**

```text
backend/app/services/rules/extractor.py
```

**Mudança:**

Adicionar:

```python
from datetime import date
```

Substituir `_extrair_data`:

```python
def _extrair_data(texto: str) -> str | None:
    """Extrai a primeira data válida dd/mm/aaaa e retorna ISO aaaa-mm-dd."""
    for match in DATA_RE.finditer(texto):
        dia, mes, ano = (int(g) for g in match.groups())

        try:
            date(ano, mes, dia)
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
| `"29/02/2024"` | `"2024-02-29"` |
| `"29/02/2023"` | `None` |

**Verificação:**

```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

## B5. CNPJ deve validar dígitos verificadores

**Arquivo:**

```text
backend/app/services/rules/extractor.py
```

Adicionar:

```python
def _cnpj_valido(cnpj: str) -> bool:
    """Valida dígitos verificadores de CNPJ usando módulo 11."""
    if len(cnpj) != 14 or not cnpj.isdigit():
        return False

    if cnpj == cnpj[0] * 14:
        return False

    def _dv(seq: str, pesos: list[int]) -> int:
        soma = sum(int(digito) * peso for digito, peso in zip(seq, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    primeiro_dv = _dv(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if primeiro_dv != int(cnpj[12]):
        return False

    segundo_dv = _dv(
        cnpj[:12] + str(primeiro_dv),
        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )
    return segundo_dv == int(cnpj[13])
```

Ajustar `_extrair_cnpj`:

```python
def _extrair_cnpj(texto: str) -> str | None:
    """Extrai o primeiro CNPJ válido do texto."""
    for match in CNPJ_RE.finditer(texto):
        raw = match.group(1)
        raw = raw.replace(".", "").replace("/", "").replace("-", "")

        if not _cnpj_valido(raw):
            continue

        return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"

    return None
```

**Casos obrigatórios:**

| Entrada | Saída |
|---|---|
| `"CNPJ 11.222.333/0001-81"` | `"11.222.333/0001-81"` |
| `"CNPJ 11.222.333/0001-00"` | `None` |
| `"CNPJ 11111111111111"` | `None` |

---

## B6. Número por extenso deve aceitar dezena composta

**Arquivo:**

```text
backend/app/services/rules/extractor.py
```

Substituir `_extrair_numero_extenso`:

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
|---|---:|
| `"prazo será vinte e um dias"` | `21` |
| `"prazo será trinta dias"` | `30` |
| `"prazo será trinta e cinco dias"` | `35` |
| `"prazo será noventa e nove dias"` | `99` |

---

## B7. Testes de regressão da Fase B

**Arquivo:**

```text
backend/tests/test_extractor.py
```

Adicionar testes cobrindo no mínimo:

```python
def test_numero_inteiro_ignora_prefixo_item():
    itens = [{
        "item_number": "4.3",
        "title": "Da Vigência",
        "content": "4.3.8 Vigência: 90 dias, com garantia.",
    }]
    regra = {
        "id": "vigencia",
        "rotulo": "Vigência",
        "tipo": "numero_inteiro",
        "ancora": "vigência",
    }

    assert extrair_valor(regra, itens) == 90


def test_numero_inteiro_grande_sem_separador():
    itens = [{
        "item_number": "1",
        "title": "",
        "content": "O quantitativo é de 10000 unidades.",
    }]
    regra = {
        "id": "qtd",
        "rotulo": "Qtd",
        "tipo": "numero_inteiro",
    }

    assert extrair_valor(regra, itens) == 10000


def test_monetario_sem_separador_milhar():
    itens = [{
        "item_number": "1",
        "title": "",
        "content": "O valor estimado é de R$ 1500,00.",
    }]
    regra = {
        "id": "valor",
        "rotulo": "Valor",
        "tipo": "monetario",
        "ancora": "valor",
    }

    assert extrair_valor(regra, itens) == 1500.0


def test_monetario_milhar_sem_centavos():
    itens = [{
        "item_number": "1",
        "title": "",
        "content": "O valor estimado é de R$ 1.500.",
    }]
    regra = {
        "id": "valor",
        "rotulo": "Valor",
        "tipo": "monetario",
        "ancora": "valor",
    }

    assert extrair_valor(regra, itens) == 1500.0


def test_data_invalida_retorna_none():
    itens = [{
        "item_number": "1",
        "title": "",
        "content": "Entrega até 31/02/2026.",
    }]
    regra = {
        "id": "entrega",
        "rotulo": "Entrega",
        "tipo": "data",
        "ancora": "entrega",
    }

    assert extrair_valor(regra, itens) is None


def test_cnpj_valido():
    itens = [{
        "item_number": "1",
        "title": "",
        "content": "Fornecedor CNPJ 11.222.333/0001-81.",
    }]
    regra = {
        "id": "cnpj",
        "rotulo": "CNPJ",
        "tipo": "cnpj",
    }

    assert extrair_valor(regra, itens) == "11.222.333/0001-81"


def test_cnpj_invalido_retorna_none():
    itens = [{
        "item_number": "1",
        "title": "",
        "content": "Fornecedor CNPJ 11.222.333/0001-00.",
    }]
    regra = {
        "id": "cnpj",
        "rotulo": "CNPJ",
        "tipo": "cnpj",
    }

    assert extrair_valor(regra, itens) is None


def test_numero_extenso_composto():
    itens = [{
        "item_number": "6.1",
        "title": "Base Legal",
        "content": "O prazo será vinte e um dias.",
    }]
    regra = {
        "id": "prazo",
        "rotulo": "Prazo",
        "tipo": "numero_extenso",
        "ancora": "prazo",
    }

    assert extrair_valor(regra, itens) == 21
```

**Verificação:**

```powershell
& $PY -m pytest tests\test_extractor.py -q
```

---

# 6. Fase C — RAG

## C1. FTS5 deve ignorar acentos

**Arquivo:**

```text
backend/app/services/rag/loader.py
```

**Objetivo:**

Permitir que `"seguranca"` encontre `"segurança"`.

**Mudança:**

No trecho de criação da tabela FTS, usar:

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

**Critérios:**

1. A tabela FTS deve ser recriada com o novo tokenizer.
2. A ingestão deve popular `legal_chunks_fts`.
3. Busca sem acento deve retornar chunk com texto acentuado.

**Verificação:**

```powershell
& $PY -m pytest tests\test_retriever.py -q
```

---

## C2. Busca híbrida com RRF

**Arquivo:**

```text
backend/app/services/rag/retriever.py
```

**Objetivo:**

Combinar busca semântica e textual usando Reciprocal Rank Fusion.

**Mudança obrigatória:**

1. Criar helper `_search_textual`.
2. Criar função `_rrf`.
3. Em `retrieve`, quando `use_semantic=True`, combinar `_search_semantic` e `_search_textual`.

Implementação de referência:

```python
async def _search_textual(db, query: str, top_k: int, law_numbers: list[str] | None) -> list[dict]:
    """Executa busca textual respeitando o dialeto do banco."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "sqlite":
        return await _search_sqlite(db, query, top_k, law_numbers)

    return await _search_postgres(db, query, top_k, law_numbers)
```

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

No `retrieve`:

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

**Critérios:**

1. Se semântica retornar vazio, usa textual.
2. Se textual falhar, mantém semântica.
3. Se ambos retornarem vazio, fluxo de fallback atual deve continuar.
4. Testes existentes de ranking devem continuar passando.

**Verificação:**

```powershell
& $PY -m pytest tests\test_retriever.py -q
```

---

## C3. Validar dimensão de embedding

**Arquivos:**

```text
backend/scripts/ingest_embeddings.py
backend/app/services/rag/retriever.py
```

**Mudança:**

Importar settings e logger, se necessário:

```python
from app.config import settings
import logging

logger = logging.getLogger(__name__)
```

No ingest:

```python
if len(vector) != settings.embeddings_dim:
    logger.warning(
        "Dimensão inesperada de embedding: esperado %d, obtido %d (chunk %s). Salvo mesmo assim.",
        settings.embeddings_dim,
        len(vector),
        chunk.id,
    )
```

No retrieve semântico:

```python
if len(query_vector) != settings.embeddings_dim:
    logger.warning(
        "Dimensão da query (%d) difere da configurada (%d). Resultados podem divergir.",
        len(query_vector),
        settings.embeddings_dim,
    )
```

**Critério:**

- Não quebrar ingestão.
- Apenas logar warning.

---

## C4. Cache limitado de embeddings de consulta

**Arquivo:**

```text
backend/app/services/rag/retriever.py
```

**Objetivo:**

Evitar re-embedding da mesma query, sem cache ilimitado.

**Implementação recomendada:**

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
    """Retorna embedding da query com cache limitado."""
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

**Atenção:**

Se `FakeEmbeddingsProvider` não tiver `provider_name`, adicionar nos testes ou na implementação fake:

```python
provider_name = "fake"
```

**Critérios:**

1. Query repetida não chama `embed` novamente.
2. Cache é limitado.
3. Testes podem limpar cache deterministicamente.

---

## C5. Testes de regressão RAG

**Arquivo:**

```text
backend/tests/test_retriever.py
```

Adicionar teste de cache:

```python
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

Adicionar teste autocontido de FTS com acento, se possível usando helper de seed próprio:

```python
def test_fts_sem_acento_retorna_chunk_acentuado():
    async def _cenario():
        Session = await _seed_sem_embeddings()
        async with Session() as db:
            return await retrieve(db, "instrucoes de seguranca", top_k=2)

    chunks = _run(_cenario())

    assert chunks
```

Se o fixture atual não garantir `segurança`, criar seed explícito com chunk contendo essa palavra.

**Verificação:**

```powershell
& $PY -m pytest tests\test_retriever.py -q
```

---

# 7. Fase D — Banco de dados

## D1. Sincronizar `db/init.sql` com models SQLAlchemy

**Arquivo:**

```text
db/init.sql
```

**Objetivo:**

Deixar o schema SQL inicial compatível com os models.

**Mudanças mínimas:**

### analyses

Adicionar:

```sql
    analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent',
```

### corrections

Adicionar:

```sql
    agent_origin VARCHAR(20),
    review_status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (review_status IN ('pendente', 'aprovada', 'rejeitada', 'ajustada')),
    review_note TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
```

### document_revisions

Se existir:

```sql
items_snapshot JSONB NOT NULL
```

Trocar para:

```sql
items_snapshot JSON NOT NULL
```

### legal_chunks

Se existir:

```sql
embedding vector(768)
```

Trocar para:

```sql
embedding TEXT
```

**Critérios:**

1. `init.sql` deve espelhar models.
2. Nenhuma coluna nova pode ficar fora do script.
3. A alteração não deve exigir pgvector.

**Verificação mínima:**

```powershell
& $PY -m py_compile ..\db\init.sql
```

> Observação: `py_compile` não valida SQL. Se houver Docker/Postgres disponível, validar com `psql`.

Validação Docker opcional:

```powershell
docker compose up -d db
docker compose exec db psql -U postgres -d licitacao -f /docker-entrypoint-initdb.d/init.sql
```

---

## D4. Script de deduplicação antes da constraint

**Arquivo novo:**

```text
backend/scripts/dedupe_comparacao_resultados.py
```

**Objetivo:**

Remover duplicados antes de criar constraint unique.

**Requisitos:**

1. Fazer backup antes.
2. Ser idempotente.
3. Imprimir quantidade de linhas removidas.
4. Funcionar para o banco configurado.

Lógica SQL base:

```sql
DELETE FROM comparacao_resultados
WHERE id NOT IN (
    SELECT MIN(id)
    FROM comparacao_resultados
    GROUP BY comparacao_id, fornecedor_id, regra_id
);
```

**Atenção:**

Se `id` não for inteiro ou não existir, adaptar para `rowid`/`ctid` ou chave primária real.

**Verificação:**

```powershell
& $PY scripts\dedupe_comparacao_resultados.py
```

---

## D2. Unique constraint em `comparacao_resultados`

**Arquivos:**

```text
backend/app/models/comparison.py
db/init.sql
```

**Model:**

Adicionar import:

```python
from sqlalchemy import UniqueConstraint
```

Na classe `ComparacaoResultado`:

```python
    __table_args__ = (
        UniqueConstraint(
            "comparacao_id",
            "fornecedor_id",
            "regra_id",
            name="uq_comparacao_fornecedor_regra",
        ),
    )
```

Se já existir `__table_args__`, incorporar a constraint sem remover as existentes.

**init.sql:**

Adicionar ao fim da tabela `comparacao_resultados`:

```sql
    CONSTRAINT uq_comparacao_fornecedor_regra
        UNIQUE (comparacao_id, fornecedor_id, regra_id)
```

**Critérios:**

1. Inserir duplicado deve falhar com erro de integridade.
2. Testes existentes devem continuar passando.
3. Script de dedupe deve rodar antes.

---

## D3. Paginação backward compatible

**Arquivos de API:**

```text
backend/app/api/documents.py
backend/app/api/analysis.py
backend/app/api/fornecedores.py
backend/app/api/comparison.py
```

**Objetivo:**

Adicionar paginação sem quebrar clientes existentes.

**Regra obrigatória:**

Não alterar o corpo da resposta atual se hoje a API retorna lista.

Implementar:

```python
from fastapi import Query, Response
from sqlalchemy import func
```

Exemplo para listagem:

```python
async def list_documents(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos com paginação compatível com clientes antigos."""
    total = (
        await db.execute(
            select(func.count()).select_from(Document)
        )
    ).scalar_one()

    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    documents = result.scalars().all()

    response.headers["X-Total-Count"] = str(total)

    return [DocumentResponse.model_validate(d) for d in documents]
```

**Critérios:**

1. `page` e `page_size` devem ser opcionais.
2. Resposta continua com o mesmo shape anterior.
3. Header `X-Total-Count` deve retornar total.
4. `page_size` máximo deve ser limitado, por exemplo `200`.
5. E2E existentes devem continuar passando.

**Verificação:**

```powershell
& $PY -m pytest tests -q
```

---

# 8. Fase E — Validação final

## E1. Suíte completa

**Comando:**

```powershell
& $PY -m pytest tests -q
```

Se E2E estiver disponível:

```powershell
& $PY -m pytest ../e2e/tests -q
```

**Critério:**

- 0 falhas.

---

## E2. Reingestão do corpus

**Comandos:**

```powershell
& $PY scripts\ingest_laws.py
& $PY scripts\ingest_juris_tcu.py
& $PY scripts\ingest_corpus_extra.py
& $PY scripts\ingest_embeddings.py
```

**Critérios:**

1. FTS recriado com `remove_diacritics 2`.
2. Chunks reindexados.
3. Embeddings salvos.
4. Busca sem acento funciona.

---

## E3. Benchmark final

**Comando:**

```powershell
& $PY scripts\benchmark.py
```

**Critério:**

Comparar:

```text
benchmark_report.before.json
benchmark_report.json
```

Métricas não podem regredir.

Se houver regressão:

1. Parar.
2. Identificar a tarefa responsável.
3. Reverter ou corrigir antes de concluir.

---

# 9. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Mudar resposta de paginação | Quebra frontend/E2E | Manter shape atual e usar `X-Total-Count` |
| Regex capturar item errado | Extração incorreta | Testes com `4.3.8`, `9.000`, `10000.` |
| FTS antigo persistir | Busca sem acento falha | Reingestão completa |
| Cache de embeddings crescer | Memória | Cache limitado com `max=256` |
| Constraint unique com duplicados | Falha de migração | Rodar dedupe antes |
| Hash novo mudar IDs | Diffs antigos | Aceitar novo padrão determinístico; não usar IDs antigos como referência |
| RRF alterar ranking | Mudança esperada | Testes de rank e benchmark |
| Banco existente divergente | Migração falha | Backup + migração manual |

---

# 10. Definition of Done revisado

A tarefa só está pronta se:

- [ ] Todas as tarefas A0–E3 foram executadas.
- [ ] `tests/` passa com 0 falhas.
- [ ] `e2e/tests` passa com 0 falhas, quando executável.
- [ ] Novos testes de regressão foram adicionados.
- [ ] `benchmark_report.json` não regrediu.
- [ ] `db/init.sql` está sincronizado com models.
- [ ] Nenhuma dependência nova foi adicionada.
- [ ] Nenhuma mudança foi feita em `database.py` ou `get_db()`.
- [ ] Nenhum segredo foi exposto.
- [ ] API continua backward compatible.
- [ ] Cache de embeddings está limitado e testado.
- [ ] FTS suporta busca sem acento.
- [ ] Parser reconhece alíneas e romanos.
- [] Extração por âncora respeita posição da âncora.
- [ ] CNPJ valida dígitos verificadores.
- [ ] Datas inválidas são rejeitadas.
- [ ] Números de item não são capturados como valor.

---

# 11. Prompt canônico para executar este PRD com IA

Você pode usar exatamente este prompt para qualquer modelo:

```text
Você é um engenheiro de software sênior executor. Sua missão é implementar o PRD "Correções de Alto Impacto no LicitAI v2.0" sem quebrar testes existentes.

Regras obrigatórias:
1. Trabalhe sempre a partir do diretório backend.
2. Use o Python do virtualenv do projeto.
3. Defina PYTHONPATH como o diretório backend quando necessário.
4. Execute as tarefas exatamente na ordem definida no PRD.
5. Após cada tarefa, rode os testes do módulo afetado.
6. Ao fim de cada fase, rode a suíte completa.
7. Se qualquer teste existente falhar, pare imediatamente, explique a causa e proponha correção mínima.
8. Não altere database.py, get_db(), .env ou contratos públicos de API sem instrução explícita.
9. Não adicione dependências.
10. Não use números de linha como referência; use nome de função e busca por trecho de código.
11. Toda correção deve incluir teste de regressão.
12. Antes de alterações de banco, verifique se a mudança é apenas para fresh install ou se exige migração.
14. Paginação deve manter backward compatibility.
15. Ao final, rode testes completos e gere relatório resumindo mudanças, arquivos alterados, testes adicionados e resultados.

Comece pela tarefa A0.
```

---

# 12. Recomendação final

O seu PRD original já é forte, mas para ser realmente executável por qualquer IA eu faria três mudanças estruturais:

## 1. Tirar referências a linhas

Trocar qualquer “linha X” por:

```text
Função: _detect_item_type
Trecho antigo: ...
Trecho novo: ...
```

## 2. Blindar compatibilidade

Deixar explícito:

```text
Nenhuma resposta de API pode mudar de shape sem atualização simultânea dos testes E2E e frontend.
```

## 3. Tornar testes autocontidos

Nenhum teste novo deve depender de fixture implícita. Cada teste deve criar o próprio cenário mínimo.

Com isso, o PRD deixa de ser apenas um bom plano técnico e vira um **runbook determinístico**, que é exatamente o formato ideal para execução autônoma por IA.