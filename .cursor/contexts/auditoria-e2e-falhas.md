# CONTEXTO — LicitAI / CODEBA — auditoria E2E + falhas recentes

Data de corte do briefing: 25/09/2026. Atualize o bloco **FATOS DO GIT** com a saída de `./scripts/contexto-auditoria.sh` antes de colar.

Idioma: PT-BR. Sem emoji. Sem hype.

Você é auditor técnico do piloto LicitAI (Next.js 14 + FastAPI + Postgres + worker).
Você NÃO implementa feature nova. Você VERIFICA e EXPLICA.

## Missão (nessa ordem)

1. Estabelecer o fato (git + containers + HTTP).
2. Rodar E2E nas 3 camadas que existirem.
3. Analisar as falhas recentes com evidência (log, teste, tela, código).
4. Entregar um relatório no formato do final deste prompt.
5. Só propor patch se a causa estiver comprovada. Sem segundo LLM no analyzer. Sem tirar TCU da quarentena.

## Fatos do repositório (não discuta — use)

- Repo: `/home/brunoadsba/licitai`
- Job do piloto: Enviar TR → Revisar agora (alto/crítico + Art. 6) → pacote SEI / HTML / DOCX
- Stack: `./scripts/up.sh` · UI `:3000` · API `:8000` · frontend Docker SEM bind mount (UI exige `--build`)
- Auth: BFF `/api/proxy/*` + `API_TOKEN`. Sem token no Postgres → 401
- Classificação: `publico|interno|sigiloso`. `sigiloso` sem Ollama → 422 (fail-closed)
- TCU: 3 peças `quarantine-0B` — fora de RAG, `legal_basis` e SEI. UI diz “Fora da análise”
- CI GitHub: desligado. Não religar
- Docs: `memory.md` · `docs/ops/e2e-full.md` · `docs/ops/gate-piloto-14d.md` · `docs/ops/deploy.md`

## Falhas recentes que VOCÊ deve auditar (não assumir “já está ok”)

### F1 — Falso positivo Art. 6º no item 1.1 (PABX nuvem)

- Sintoma: correção acusa falta de quantitativo/prazo/prorrogação e sugere `[quantidade]` / `[prazo]`. Art. 6º, XXIII, a é do TR, não do §1.1. Dados em 1.4 (24 meses), 4.3.2 (130 ramais), 11.5 (prorrogação).
- Código em `main` (`7846070`): G2 `\[[^\]]{1,80}\]`, G4 + sinônimos, `document_inventory.py`, instrução 4 do prompt.
- Régua: `backend/tests/test_analysis_precision.py`
- Pendente humano: reenviar `fixtures/trs-codeba/piloto-unico/09-ti-pabx-nuvem.pdf` em modo econômico e CONFERIR o 1.1 na UI.
- Critério de passe: 1.1 NÃO ganha correção com `[prazo]` / `[quantidade]` / omissão Art. 6 (a) se o fato está em outro item.

### F2 — Copiloto: faixa estreita + resposta com ruído

- Sintoma: painel à direita (`sm:max-w-md`). Resposta com UUID, `estrutural:failed`, `source_id`, rodapé do parecer (“Fontes do parecer: correções …”).
- Branch `feat/copiloto-ux` (pode estar só local, sem merge): Dialog centralizado; `answer_sanitize.py`; prompt guia (Resposta / O que fazer agora / Onde está no TR); fontes sem rodapé de IDs; correção operacional fora do catálogo.
- Conferir: `git branch --show-current` · `git log -1 --oneline` · se `feat/copiloto-ux` está em `main` ou não.
- Critério de passe (se a branch estiver no container): Perguntar abre no centro, quase tela cheia; resposta sem UUID e sem `estrutural:failed`.

### F3 — `./scripts/up.sh --build` falhou no smoke

- Sintoma: imagens OK, containers recreated, livez/readyz 200, depois `curl: (56) Recv failure` em `/api/docs` e `frontend/` HTTP 000.
- Causa típica: smoke imediato após recreate; Next.js ainda não escuta :3000.
- Conferir se `scripts/smoke_readyz.sh` tem retry (até 10 × 2s). Se o arquivo no disco tem o loop e o smoke agora passa, F3 é corrida, não regressão de produto.
- Critério de passe: `./scripts/smoke_readyz.sh` → 200 em livez, readyz, metrics, api/docs, frontend/, frontend/readyz; 4 containers healthy.

### F4 — Precisão humana baixa (histórico, não reabrir 5–8 RAG)

- Análise `afd39876…` (16/09): 9 rejeitadas, 1 aprovada, 1 ajustada → precisão 0.09–0.18.
- Classes: cláusula isolada, números inventados, lei/regime errado, trecho do RAG, ruído operacional como achado, fatia truncada.
- Gate G1–G4 existe desde 18/09. F1 era o buraco que o gate antigo não pegava.
- Não relançar ingestão TCU, HNSW, nem `rag_rerank_mode=llm`.

### F5 — WIP fora desta auditoria (só registrar, não misturar)

- Stash `wip classificacao-padrao-publico`: default `publico` no form. NÃO misturar no E2E desta sessão salvo o Bruno pedir.
- Fine-tune / OIDC / K8s / CI: fora.

## Leitura obrigatória (nessa ordem; não leia o repo inteiro)

1. Bloco FATOS DO GIT (saída do script) ou `git status` · `git branch -vv` · `git log -8 --oneline`
2. `memory.md` — blocos “Pendências em aberto”, “Agora”, journal 16–25/09
3. `docs/ops/e2e-full.md`
4. `backend/app/services/analyzer/evidence_gate.py` + `document_inventory.py` + trecho da instrução 4 em `prompts.py`
5. `frontend/src/components/chat/ChatCopilot.tsx` + `backend/app/services/chat/answer_sanitize.py` (se existirem)
6. `scripts/smoke_readyz.sh` · `scripts/up.sh`

## Protocolo E2E (execute; não descreva só)

Pré: Docker/WSL ligados. `unset POSTGRES_PASSWORD DATABASE_URL`.

### Camada 0 — stack

```bash
# Se a stack já está up (smoke recente 200), NÃO rebuild. Só:
./scripts/smoke_readyz.sh
./scripts/smoke_e2e_compose.sh
```

Se 000/unhealthy: esperar 20s e repetir. Só `--build` se a UI da branch não estiver na imagem.

### Camada 1 — API

```bash
cd /home/brunoadsba/licitai
E2E_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=backend:e2e/tests \
  pytest e2e/tests -m e2e_fast -v --tb=short
```

No backend (régua das falhas, sem LLM):

```bash
cd /home/brunoadsba/licitai/backend
pytest tests/test_analysis_precision.py tests/test_chat_answer_sanitize.py \
  tests/test_chat_validator.py tests/test_privacy.py -q --tb=short
```

`e2e_live` / LLM longo: SÓ se o Bruno autorizar cota. Não estourar Groq/Gemini.

### Camada 2 — UI (humano + máquina)

- Abrir http://127.0.0.1:3000/
- Playwright só se `E2E_LIVE=1` e stack healthy:

```bash
cd /home/brunoadsba/licitai/frontend
E2E_LIVE=1 E2E_BASE_URL=http://127.0.0.1:3000 npx playwright test e2e/smoke.spec.ts
```

- Manual F1: reupload 09-ti-pabx-nuvem, econômico, esperar completed/completed_with_errors, abrir item 1.1.
- Manual F2: botão Perguntar na análise. Anotar se é faixa direita ou diálogo centro; se a resposta tem UUID/`estrutural:failed`.

## Método de análise (obrigatório)

Para cada falha F1–F3:

1. **Sintoma observado agora** (comando, HTTP, trecho de log, o que a UI mostrou).
2. **Causa** em uma frase (com arquivo:linha se possível).
3. **Estado do código**: em main / só na branch / só no working tree / não existe.
4. **Estado do runtime**: a imagem Docker inclui esse código? (frontend sem bind mount).
5. **Veredito**: PASSOU | FALHOU | NÃO TESTÁVEL (e por quê).
6. **Próximo passo único** — o mais barato que fecha o risco.

Não culpe “a IA”. Separe: gate determinístico vs prompt vs imagem velha vs smoke precoce vs cota LLM.

## Formato da entrega (só isto; sem preâmbulo)

### 1. Fato

- branch, HEAD, working tree sujo? stash?
- 4 containers: healthy/starting/unhealthy
- smoke_readyz: OK/FALHA

### 2. E2E

| Camada | Comando | Resultado | Nota |
|--------|---------|-----------|------|
| 0 smoke | … | … | … |
| 1 e2e_fast | … | … | … |
| 1 precision/chat | … | … | … |
| 2 UI / Playwright | … | … | … |

### 3. Falhas recentes

Tabela F1 F2 F3 (F4/F5 só se aparecer evidência nova).

### 4. Conclusão em 5 linhas

O que está seguro no piloto hoje. O que o Bruno deve fazer com as mãos (re-run ouro, rebuild, merge). O que NÃO fazer.

### 5. Se algo falhou de verdade

Um patch mínimo OU um comando de verificação. Sem plano de 8 semanas.
