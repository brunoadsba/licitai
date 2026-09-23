<!--
Origem: plano técnico ajustado pós-auditoria, 23/09/2026.
Texto integral colado na conversa de revisão (thread 1fde8fc0-4391-4006-8260-4d6d27269029).
Conteúdo do plano não foi reescrito; apenas arquivado neste repositório.
-->

# Plano técnico ajustado para o LicitAI

## 1. Decisão executiva

O LicitAI deve continuar como um monólito FastAPI com PostgreSQL, pgvector e worker assíncrono. A auditoria não justifica uma migração imediata para microserviços, outro banco vetorial ou uma reescrita do produto.

A prioridade não é aumentar a capacidade do modelo nem ampliar o corpus. A prioridade é impedir respostas fundamentadas em dados jurídicos não confiáveis, impedir o envio de documentos sigilosos a provedores não autorizados e tornar cada correção e resposta auditável.

O plano ajustado começa com contenção de riscos. Em seguida, cria uma base de avaliação e rastreabilidade. Só depois altera o modelo jurídico, o pipeline de ingestão e a recuperação.

> **Regra operacional imediata:** até a conclusão da contenção de sigilo, não devem ser enviados ao piloto documentos classificados como sigilosos.

O plano foi organizado em quatro ondas:

1. **Contenção:** bloquear vazamentos e retirar fontes não verificadas da busca ativa.

1. **Auditabilidade:** registrar recuperação, fontes, versões e métricas.

1. **Qualidade do RAG:** corrigir corpus, versionamento, chunking e recuperação.

1. **Produto e escala:** melhorar experiência, custos, operação e preparar multiusuário quando houver requisito real.

---

## 2. Escopo e premissas

O LicitAI é um revisor de Termos de Referência da CODEBA, com sugestões no formato DE→PARA, revisão humana e exportação para o SEI. Também possui um copiloto de chat. O RAG jurídico apoia essas duas funções; ele não deve ser tratado como um simples chatbot de legislação.

A arquitetura observada é composta por Next.js 14, uma camada BFF, uma API FastAPI monolítica, PostgreSQL 16 com pgvector, uma fila de jobs no banco e um worker assíncrono. Há integração com Groq, Gemini e Ollama. O corpus contém leis, RILC CODEBA e documentos relacionados ao TCU.

O plano assume que:

- o piloto ainda é single-user e executado localmente;

- documentos de Termos de Referência podem conter informação sigilosa;

- o corpus jurídico precisa preservar histórico, mas a busca padrão deve priorizar a redação vigente;

- a aprovação humana continua obrigatória antes da cópia para o SEI;

- as decisões jurídicas finais não são automatizadas pelo sistema;

- toda alteração será implementada em branches próprias e validada por testes.

A auditoria disponível não confirmou o estado do banco em execução, a existência efetiva do índice HNSW, a execução dos testes, as vulnerabilidades atuais das dependências nem o conteúdo oficial das fontes TCU. Esses itens devem ser confirmados nas fases correspondentes.

---

## 3. Priorização corrigida dos achados

A classificação abaixo separa o que foi comprovado no código do que ainda depende de confirmação jurídica ou operacional.

| ID | Achado | Classificação ajustada | Tratamento |
| --- | --- | --- | --- |
| F04 | Documento sigiloso pode chegar a cloud por failover, embeddings ou chat | P0 confirmado | Corrigir imediatamente |
| F01 | Corpus possui duplicações e não representa vigência | P0 quando usado em produção; P1 no piloto | Quarentenar e versionar |
| F02a | Corpus TCU não tem fonte específica e mistura enunciado com comentário | P1 confirmado | Retirar da busca ativa |
| F02b | Atribuição de súmula ou acórdão pode estar incorreta | P1 suspeito | Confirmar com fonte oficial |
| F07 | Citação do chat pode exibir texto gerado pelo LLM | P1 confirmado | Montar no servidor |
| F03 | API fica sem autenticação no Compose atual | P1 se houver exposição; P2 se estritamente local | Tornar fail-closed |
| F08 | Dados externos não estão uniformemente delimitados nos prompts | P1 confirmado | Unificar montador de prompts |
| F05 | Busca textual PostgreSQL usa ILIKE sem ranking e possui risco de precedência | P1 confirmado | Corrigir e testar no PostgreSQL |
| F06 | Caminho pgvector não é usado; índice precisa de confirmação | P1 confirmado quanto ao fallback; hipótese quanto ao índice | Confirmar no banco antes de migrar |
| F09 | Reingestão apaga registros e cria IDs instáveis | P1 confirmado | Implementar versões imutáveis |
| F10 | Chunking não preserva hierarquia e há truncamento agressivo | P1 confirmado | Migrar para dispositivos hierárquicos |
| F11 | Não há avaliação confiável no corpus real | P1 confirmado | Criar conjunto curado |
| F12 | Não há rastro persistente da recuperação | P1 confirmado | Criar retrieval_run |
| F13 | Extensão pode inserir HTML não escapado e depende de API aberta | P1 confirmado, sujeito à confirmação da superfície do SEI | Corrigir antes de uso ampliado |
| F14 | Parse e OCR podem bloquear a requisição | P2 confirmado | Mover para o worker |
| F15 | Não há orçamento de custo por usuário ou endpoint | P2 no piloto; P1 em uso ampliado | Instrumentar e limitar |
| F16 | Contexto controlado pelo cliente e IDOR estrutural | P1 para multiusuário; P2 no single-user local | Corrigir antes de multiusuário |
| F17 | Reexecução de job pode duplicar correções | P2, ainda não confirmado | Testar idempotência |
| F18 | Cache em memória pode ficar desatualizado após reingestão | P2 confirmado | Limitar e invalidar por versão |
| F19 | Feedback negativo grava conteúdo em arquivo do repositório | P2 confirmado | Mover para armazenamento apropriado |
| F20 | Parser DOCX pode perder ordem, cabeçalhos e notas | P2 confirmado | Criar fixtures e corrigir |
| F21 | Parecer e nota são gerados sem fontes explícitas | P1 para uso jurídico; P2 no piloto | Vincular a evidências das correções |
| F22 | Backend roda como root e imagem não exclui arquivos desnecessários | P3 no piloto; P2 em produção | Corrigir na fase operacional |
| F23 | CI está desativado | P2 confirmado | Reativar antes de ampliar o piloto |
| F24 | Dependências não foram auditadas | P3 até confirmação | Executar auditoria de dependências |

### 3.1 Regra para P0

Um achado é P0 quando pode causar vazamento de documento sigiloso ou produzir uma fundamentação jurídica que o produto apresenta como vigente sem possuir evidência confiável. P0 não significa necessariamente que toda implementação deva ser feita em uma única branch; significa que o uso afetado deve ser bloqueado até existir uma mitigação testada.

---

## 4. Estado final desejado

Ao final das primeiras quatro fases, o LicitAI deverá cumprir estas condições:

- nenhuma chamada cloud ocorre para documento sigiloso quando cloud não estiver autorizada;

- failover e embeddings obedecem à mesma política de privacidade da geração;

- fontes TCU não verificadas não participam da recuperação padrão;

- documentos jurídicos possuem versão, hash, origem e status;

- a busca padrão exclui versões revogadas ou históricas, salvo consulta explícita;

- toda resposta e correção guarda os dispositivos recuperados e a versão do corpus;

- citações são montadas pelo servidor a partir do texto canônico;

- o conjunto de avaliação roda no PostgreSQL real;

- o CI detecta regressões de recuperação e segurança;

- o piloto permanece single-user até que exista autenticação e autorização por recurso.

---

# Onda 1 — Contenção imediata

## Fase 0A — Bloqueio de vazamento de sigilo

### Objetivo

Criar uma política única e fail-closed para determinar quais provedores podem receber cada documento ou consulta. A política deve ser aplicada antes de qualquer chamada a LLM, embedding, reranking ou fallback.

### Problemas tratados

F04, parte de F15 e parte de F16.

### Escopo

Não alterar ainda o modelo jurídico, o chunking, o banco vetorial ou a arquitetura multiusuário. A fase deve resolver apenas a circulação de dados entre o sistema e os provedores.

### Implementação

1. Criar uma política central, por exemplo `ProviderPolicy`, que receba:
  - classificação do documento;
  - provedor solicitado;
  - tipo da chamada: geração, embedding, consulta, chat ou reranking;
  - ambiente de execução;
  - configuração de autorização cloud.

1. Adotar comportamento fail-closed:
  - se a classificação estiver ausente, usar a classificação mais restritiva definida para o piloto;
  - se a política não puder ser calculada, bloquear o envio;
  - se o provedor local falhar e cloud não estiver autorizada, retornar erro controlado;
  - nunca fazer fallback silencioso para cloud.

1. Aplicar a política a:
  - LLM primário;
  - failover;
  - embeddings de documentos;
  - embeddings de consultas;
  - chat;
  - reranking;
  - jobs reexecutados.

1. Passar explicitamente as variáveis de ambiente necessárias ao backend e ao worker.

1. Registrar no log apenas:

   Nunca registrar conteúdo do documento, prompt, token ou segredo.
  - decisão de política;
  - classificação;
  - tipo de chamada;
  - provedor permitido ou bloqueado;
  - request ID.

1. Adotar uma classificação padrão conservadora para uploads sem classificação explícita. A mudança do padrão deve ser documentada na UI e no backend.

### Arquivos prováveis

`services/privacy.py`, `services/llm/provider.py`, `services/llm/factory.py`, `services/embeddings/*`, `rag/semantic.py`, `chat/service.py`, `config.py`, `docker-compose.yml`, serviços de upload e worker.

### Testes obrigatórios

- documento sigiloso com cloud proibida não chama Groq;

- documento sigiloso com cloud proibida não chama Gemini;

- embedding de documento sigiloso não chama Gemini;

- embedding de consulta vinculada a documento sigiloso não chama Gemini;

- failover local para cloud é bloqueado;

- reranking cloud é bloqueado;

- configuração ausente bloqueia a chamada;

- documento público pode usar os provedores autorizados;

- o teste falha se qualquer mock cloud for acionado;

- logs não contêm conteúdo do documento.

### Critérios de aceite

- zero chamadas cloud nos testes de sigilo;

- zero fallback proibido;

- política única usada por geração, embedding, chat e reranking;

- smoke test concluído com Ollama e documento sigiloso;

- documentação operacional atualizada.

### Rollback

O rollback só pode reativar o comportamento anterior em ambiente de desenvolvimento e com documentos não sigilosos. Não é permitido fazer rollback para um modo que envie sigilosos à cloud no piloto.

---

## Fase 0B — Quarentena do corpus TCU não verificado

### Objetivo

Remover da recuperação padrão as fontes TCU que não possuem fonte específica, sem destruir os dados necessários para revisão jurídica.

### Problemas tratados

F02a, F02b e F21.

### Implementação

1. Marcar os itens como `quarantine` ou equivalente.

1. Excluir fontes em quarentena da recuperação padrão.

1. Impedir que referências em quarentena sejam usadas em `legal_basis` ou no parecer final.

1. Preservar o script, os dados originais e o motivo da quarentena em local auditável.

1. Criar uma lista de fontes pendentes de confirmação.

1. Reingerir apenas após obter:
  - URL oficial específica;
  - título oficial;
  - data de coleta;
  - hash;
  - separação entre enunciado e comentário;
  - revisão jurídica.

### Critérios de aceite

- nenhum item em quarentena aparece em resultados padrão;

- nenhuma citação aponta para fonte em quarentena;

- o material não é apagado sem registro;

- o sistema informa ausência de fonte quando a consulta depender exclusivamente desse material.

---

## Fase 0C — Autenticação operacional e extensão SEI

### Objetivo

Fechar o acesso acidental à API no piloto e eliminar a montagem insegura de HTML na extensão.

### Problemas tratados

F03 e F13.

### Implementação

1. Tornar `X-API-Token` obrigatório em qualquer ambiente com PostgreSQL.

1. Configurar `APP_ENV` explicitamente no Compose.

1. Proteger ou desativar `/api/docs`, `/openapi.json` e rotas equivalentes fora do desenvolvimento.

1. Fazer a extensão usar o caminho autenticado pelo BFF ou um mecanismo explicitamente aprovado.

1. Escapar todo conteúdo antes de inseri-lo no editor do SEI.

1. Preferir o endpoint `corrected-html` já escapado.

1. Não tratar o token compartilhado como autenticação multiusuário. Documentar que ele é contenção operacional do piloto.

### Testes

- todas as rotas `/api/v1` respondem 401 sem token;

- documentação fica indisponível fora do desenvolvimento;

- extensão funciona com autenticação;

- conteúdo com `<img onerror>`, `<script>` e atributos HTML é neutralizado;

- nomes de arquivo e conteúdo não alteram a estrutura do editor.

### Critérios de aceite

A API não fica aberta por ausência acidental de variável de ambiente. A extensão não injeta HTML controlado por documento ou nome de arquivo.

---

# Onda 2 — Auditabilidade e base de avaliação

## Fase 1 — Registro de recuperação e claims

### Objetivo

Tornar possível reconstruir quais fontes sustentaram cada resposta, correção e parecer.

### Problemas tratados

F07, F12 e F21.

### Modelo mínimo

Criar uma entidade `retrieval_run` com:

- `id`;

- `request_id`;

- `operation_type` — análise, chat, embedding ou avaliação;

- `query_hash`;

- `corpus_version`;

- `created_at`;

- modelo de embedding;

- modelo de reranking;

- parâmetros de recuperação;

- lista ordenada de dispositivos recuperados;

- scores de cada etapa;

- filtros aplicados;

- classificação de privacidade.

Criar ou adaptar entidades de evidência e claim:

- `evidence_id`;

- documento e versão;

- dispositivo;

- texto canônico;

- página ou localização;

- hash da fonte;

- `claim_id`;

- afirmação produzida;

- evidências vinculadas;

- status de validação.

### Regras de geração

O LLM não deve fornecer livremente `reference`, `title` e `snippet` exibidos ao usuário. Ele deve retornar apenas identificadores estruturados das evidências permitidas e, quando necessário, uma afirmação interpretativa separada.

O servidor deve:

1. verificar se o ID pertence ao contexto entregue ao LLM;

1. carregar o texto canônico do banco;

1. montar a citação;

1. informar norma, versão, status, dispositivo e origem;

1. marcar a diferença entre texto normativo e interpretação;

1. rejeitar referências fora do contexto.

Substring normalizada pode ser usada como primeira validação, mas não deve ser a única prova de suficiência da evidência.

### Critérios de aceite

- toda análise e resposta de chat possui `retrieval_run`;

- IDs dos dispositivos recuperados são persistidos;

- a versão do corpus é calculada por hash ou manifesto imutável;

- o texto exibido em citações vem do servidor;

- referências fora do contexto são rejeitadas;

- pareceres apontam para as correções e evidências de origem.

---

## Fase 2 — Avaliação real, CI e linha de base

### Objetivo

Criar uma medição confiável antes de alterar recuperação ou corpus.

### Problemas tratados

F11, F23 e parte de F06.

### Estratégia

O harness atual, baseado em chunks sintéticos e SQLite, deve permanecer como teste unitário, mas não pode ser tratado como avaliação de produção.

Criar um conjunto curado sobre o corpus real. Cada caso deve possuir:

- pergunta;

- intenção;

- categoria;

- norma e versão esperadas;

- dispositivos esperados;

- trechos obrigatórios;

- resposta aceitável;

- resposta obrigatória quando não houver evidência;

- métricas;

- tolerância;

- curador;

- data de curadoria.

### Categorias mínimas

- localização de artigo, inciso e alínea;

- definições;

- exceções;

- perguntas multi-hop;

- comparação entre regimes;

- vigência;

- alteração e revogação;

- jurisdição;

- perguntas sem resposta no acervo;

- consultas ambíguas;

- documentos longos;

- anexos e tabelas;

- prompt injection;

- tentativa de acessar documento não autorizado.

### Métricas

- Recall@1 e Recall@5;

- MRR;

- nDCG@5;

- taxa de citação literal válida;

- taxa de citação correta por dispositivo;

- taxa de resposta sem evidência;

- falso positivo de resposta;

- falso negativo de recusa;

- latência p50 e p95;

- custo por operação;

- taxa de erro por provedor.

### Ordem de execução

1. criar o formato do conjunto;

1. curar uma amostra pequena com revisão jurídica;

1. executar no PostgreSQL real;

1. registrar a baseline junto da versão do corpus;

1. reativar o CI;

1. fazer o CI falhar diante de regressão acima da tolerância.

Uma tolerância provisória pode ser não regredir mais de dois pontos percentuais por categoria, até o negócio aprovar metas absolutas.

### Critérios de aceite

- avaliação reproduzível;

- execução contra PostgreSQL;

- resultados versionados;

- CI ativo;

- casos de segurança incluídos;

- linha de base revisada por curador jurídico.

---

# Onda 3 — Qualidade jurídica e recuperação

## Fase 3 — Pipeline de ingestão confiável

### Objetivo

Tornar a ingestão idempotente, reprodutível, rastreável e segura contra perda de contexto jurídico.

### Problemas tratados

F01, F09, F14 e F20.

### Implementação

1. Separar download, extração, normalização, validação, versionamento e indexação.

1. Registrar origem, URL, data de coleta, hash e resultado da extração.

1. Preservar trechos tachados como redação histórica, em vez de tratá-los como texto vigente.

1. Tratar marcações como `(VETADO)` e `(Redação dada pela...)` de forma estruturada.

1. Registrar falhas de cada documento e permitir reprocessamento.

1. Fazer o parser retornar uma estrutura intermediária validável antes da persistência.

1. Mover parsing pesado e OCR para o worker.

1. Tornar duas execuções idempotentes.

1. Corrigir o parser DOCX para preservar ordem, cabeçalhos, notas e localização quando possível.

### Critérios de aceite

- duas execuções com a mesma fonte produzem o mesmo estado lógico;

- hashes permanecem estáveis;

- falhas são registradas e reprocessáveis;

- fixtures com tachado não misturam redação histórica e vigente;

- documentos incompletos não são publicados silenciosamente;

- OCR possui timeout que encerra efetivamente o processo;

- upload não bloqueia a requisição durante parse pesado.

---

## Fase 4 — Modelo jurídico versionado

### Objetivo

Representar a norma, suas versões, seus dispositivos e sua validade sem destruir o histórico.

### Problemas tratados

F01, F02, F09 e F10.

### Modelo sugerido

`legal_works` representa a norma como entidade estável:

- número;

- título;

- tipo;

- órgão emissor;

- esfera;

- jurisdição;

- área temática.

`legal_versions` representa uma versão:

- URL;

- data de coleta;

- hash;

- redação;

- status;

- vigência inicial;

- vigência final;

- norma alteradora;

- fonte de validação.

`legal_provisions` representa dispositivos:

- versão;

- caminho hierárquico;

- artigo;

- parágrafo;

- inciso;

- alínea;

- item;

- `parent_id`;

- texto canônico;

- status;

- hash do dispositivo.

### Regras

- versões são imutáveis;

- alterações criam nova versão ou relação explícita de alteração;

- a busca padrão filtra status vigente;

- histórico só aparece quando solicitado;

- dispositivos devem preservar caput e ancestrais relevantes;

- o corpus TCU só retorna quando a fonte estiver validada.

### Migração

Não apagar o modelo antigo imediatamente. Criar uma tabela de mapeamento do ID antigo para o novo dispositivo, migrar uma amostra, comparar resultados e só então publicar o novo índice.

### Critérios de aceite

- todo dispositivo tem norma, versão, URL, data de coleta, hash e status;

- não há duas redações com status vigente para o mesmo caminho;

- histórico permanece consultável de forma explícita;

- vigência é filtrável no banco;

- uma amostra é revisada por curador jurídico.

---

## Fase 5 — Recuperação PostgreSQL e contexto hierárquico

### Objetivo

Fazer a busca de produção funcionar no banco real e entregar ao LLM contexto suficiente para não perder exceções.

### Problemas tratados

F05, F06, F10 e F18.

### Implementação textual

Substituir o `ILIKE` sem ranking por busca PostgreSQL apropriada, usando o índice disponível ou uma versão equivalente validada. O código deve:

- normalizar acentos;

- tratar stopwords;

- usar ranking textual;

- agrupar corretamente `OR` e filtros;

- aplicar filtros de vigência;

- aceitar consulta direta por artigo;

- manter regime, jurisdição e norma como filtros estruturados.

### Implementação vetorial

Antes de decidir entre `vector`, `halfvec` ou redução de dimensão, confirmar no PostgreSQL:

- tipo da coluna;

- versão do pgvector;

- existência do índice;

- plano de execução;

- uso real do índice;

- latência;

- recall.

A escolha final deve ser baseada em teste no ambiente de homologação, não apenas em documentação.

### Contexto hierárquico

Para um dispositivo recuperado, entregar ao modelo:

- o dispositivo específico;

- o caput quando necessário;

- ancestrais hierárquicos;

- exceções e parágrafos relacionados;

- versão e vigência;

- localização da fonte.

O orçamento deve ser de tokens, não de caracteres fixos de 400 ou 2.500. O sistema deve preferir reduzir o número de dispositivos antes de cortar silenciosamente o final de um artigo.

### Cache

- limitar tamanho;

- associar à versão do corpus;

- invalidar após reingestão;

- evitar cache cruzado entre classificações de privacidade;

- registrar hit e miss.

### Critérios de aceite

- FTS e vetor são exercitados em PostgreSQL;

- o plano de execução demonstra o caminho esperado;

- consultas por artigo recuperam o dispositivo correto;

- filtros de vigência funcionam;

- artigos extensos não perdem exceções relevantes;

- a avaliação não sofre regressão superior à tolerância;

- p95 atende à meta aprovada.

---

# Onda 4 — Produto, operação e escala

## Fase 6 — Grounding, citações e geração

### Objetivo

Separar texto normativo de interpretação e impedir que o sistema apresente fundamentação inventada.

### Problemas tratados

F07, F08, F10 e F21.

### Implementação

1. O LLM retorna claims e IDs de evidência, não texto de citação livre.

1. O servidor gera a citação a partir do dispositivo canônico.

1. A UI mostra:
  - norma;
  - versão;
  - status;
  - artigo e subdispositivo;
  - URL oficial;
  - página, quando houver;
  - trecho literal;
  - indicação de interpretação da IA.

1. O `LegalAgent` não deve emitir fundamento jurídico quando não recebeu contexto RAG suficiente.

1. O parecer final deve apontar para as correções e suas evidências.

1. O bypass para respostas curtas deve ser restrito a saudações e casos determinados pelo servidor.

1. A confiança informada pelo LLM não deve ser tratada como métrica calibrada sem validação.

### Critérios de aceite

- toda afirmação factual relevante aponta para evidência;

- trecho exibido existe na fonte após normalização;

- dispositivo citado pertence ao contexto entregue;

- versão e status são exibidos;

- respostas sem evidência são recusadas ou qualificadas;

- prompt injection não muda regras, fontes ou classificação;

- parecer e nota têm rastreabilidade até correções e fontes.

---

## Fase 7 — Performance, custo e disponibilidade

### Objetivo

Controlar custo e latência sem alterar a qualidade jurídica de forma silenciosa.

### Problemas tratados

F14, F15, F18, F22 e F24.

### Implementação

- orçamento por endpoint e por operação;

- contagem de tokens;

- cache persistente de embeddings de consulta, respeitando privacidade;

- limites de tamanho e tempo para OCR, DOCX e ODT;

- processo backend não-root;

- `.dockerignore`;

- auditoria de dependências;

- métricas p50 e p95;

- alertas de custo e erro;

- health checks do banco, worker e provedores;

- teste de carga com jobs e chat.

A redução de dimensão de embeddings só deve ser feita depois de medir o impacto em recall.

### Critérios de aceite

- custo por análise e chat é registrado;

- limites de custo funcionam;

- parse malformado não bloqueia indefinidamente o worker;

- dependências críticas são auditadas;

- imagem roda com usuário não-root;

- carga definida pelo SLO não gera 5xx acima da tolerância.

---

## Fase 8 — Experiência de auditoria jurídica

### Objetivo

Tornar o resultado compreensível e verificável para o revisor humano.

### Implementação

A UI deve permitir:

- abrir o texto integral do dispositivo;

- navegar até artigo, parágrafo, inciso e alínea;

- distinguir texto normativo de interpretação;

- visualizar versão, vigência e fonte;

- visualizar a evidência de cada correção DE→PARA;

- consultar o rastro da análise;

- exportar o pacote de auditoria junto com o resultado;

- registrar aprovação, rejeição e justificativa do revisor.

### Critérios de aceite

Um revisor deve conseguir, sem consultar logs técnicos, responder:

- qual texto foi alterado;

- por que foi alterado;

- qual norma fundamentou a alteração;

- qual versão da norma foi usada;

- qual trecho comprova a fundamentação;

- quem aprovou a correção;

- quando a análise ocorreu.

---

## Fase 9 — Preparação para multiusuário

### Condição de entrada

Só iniciar quando existir requisito real de uso por mais de um usuário ou organização. Não antecipar OIDC ou arquitetura multi-tenant sem necessidade, mas não expandir o piloto com o token compartilhado como se ele fosse autenticação completa.

### Implementação

- identidade individual;

- organizações e tenants;

- autorização por recurso;

- filtro de documentos antes e depois da recuperação;

- testes de IDOR/BOLA;

- auditoria por usuário;

- rotação e revogação de credenciais;

- política de retenção;

- segregação de cache;

- controle de acesso administrativo.

### Critérios de aceite

- usuário não acessa documento, análise, conversa ou correção de outro usuário;

- recuperação aplica filtros de autorização;

- cache não atravessa tenants;

- todas as ações críticas possuem identidade e timestamp;

- testes negativos cobrem acesso direto por ID.

---

# 5. Suíte de avaliação RAG

## 5.1 Formato de caso

Cada caso deve ser versionado em JSONL com estes campos:

```json
{
  "id": "vigencia-001",
  "categoria": "vigencia",
  "pergunta": "...",
  "intencao": "...",
  "dificuldade": "alta",
  "documentos_esperados": ["..."],
  "dispositivos_esperados": ["..."],
  "trechos_obrigatorios": ["..."],
  "resposta_esperada": "...",
  "citacoes_obrigatorias": ["..."],
  "resposta_aceitavel_sem_evidencia": "...",
  "metrica": "recall_at_5",
  "tolerancia": 0.02,
  "curador": "...",
  "data_curadoria": "..."
}
```

## 5.2 Casos obrigatórios

O conjunto deve cobrir:

- artigo, parágrafo, inciso e alínea;

- definição legal;

- exceções;

- comparação entre Lei 14.133 e Lei 13.303;

- RILC CODEBA;

- vigência e redação histórica;

- revogação;

- norma alteradora;

- perguntas fora da jurisdição ou fora do corpus;

- perguntas sem resposta;

- consultas ambíguas;

- artigos longos;

- anexos e tabelas;

- múltiplas fontes;

- prompt injection dentro do TR;

- acesso não autorizado, quando multiusuário existir.

## 5.3 Metas

As metas absolutas de recall e groundedness devem ser aprovadas após a baseline. Até lá:

- não regredir mais de dois pontos percentuais por categoria;

- zero citação para fonte em quarentena;

- zero documento revogado em consulta de legislação vigente;

- 100% das citações devem ser textualmente verificáveis;

- 100% dos testes de isolamento devem bloquear acesso indevido;

- 100% dos testes de sigilo devem impedir chamadas cloud proibidas.

---

# 6. Plano de execução no Cursor

## 6.1 Regra de operação

Cada fase deve ser executada em branch própria. O agente deve alterar somente a fase solicitada, criar testes antes ou junto da implementação e apresentar o diff antes de avançar.

Não pedir ao agente para “implementar toda a auditoria”. Isso mistura contenção, migração, recuperação e produto em uma única mudança difícil de validar.

## 6.2 Modelo recomendado

- **Claude Opus 5.5:** revisão arquitetural, decisões de privacidade, modelo jurídico e revisão de diffs críticos.

- **Grok 4.7:** implementação das fases e execução de testes no repositório.

- **Composer 2.5 ou Gemini 3.8 Flash:** tarefas mecânicas, documentação, fixtures, testes simples e análise de volume.

## 6.3 Prompt-base de implementação

```
Implemente somente a fase descrita abaixo no projeto LicitAI.

Fase: [NOME DA FASE]

Restrições:
- não implemente fases futuras;
- não faça refatorações não relacionadas;
- não altere contratos públicos sem explicar o impacto;
- não remova dados sem migração ou registro;
- não execute comandos destrutivos;
- preserve a aprovação humana antes da exportação para o SEI.

Antes de editar:
1. leia os arquivos envolvidos;
2. descreva o fluxo atual;
3. liste os arquivos que serão alterados;
4. descreva a estratégia;
5. liste riscos, dependências e plano de rollback;
6. liste os testes que serão criados ou ajustados.

Durante a implementação:
- faça mudanças pequenas e revisáveis;
- mantenha compatibilidade quando possível;
- registre decisões que dependam de hipótese;
- trate falhas de segurança com comportamento fail-closed.

Depois da implementação:
1. execute os testes seguros relacionados;
2. revise o diff;
3. informe os arquivos alterados;
4. informe o que foi validado;
5. informe o que não foi validado;
6. informe riscos residuais;
7. não avance para outra fase.
```

## 6.4 Prompt para revisão crítica

```
Atue como auditor independente do diff desta fase do LicitAI.

Não altere o código. Procure:
- regressões de segurança;
- chamadas cloud proibidas;
- perda de rastreabilidade;
- referências que o LLM possa inventar;
- mistura entre texto normativo e interpretação;
- falhas de autorização;
- migrações destrutivas;
- testes que passam sem validar o caminho de produção;
- efeitos sobre a exportação para o SEI.

Para cada problema, informe:
- severidade;
- confiança;
- evidência no diff ou no código;
- impacto;
- correção recomendada;
- teste necessário.

Conclua com:
- aprovado;
- aprovado com ressalvas;
- reprovado.
```

---

# 7. Ordem prática recomendada

A sequência de execução deve ser:

1. Fase 0A: bloquear vazamento de sigilo.

1. Fase 0B: colocar TCU não verificado em quarentena.

1. Fase 0C: fechar API e corrigir extensão.

1. Fase 1: registrar retrieval runs, evidências e claims.

1. Fase 2: criar avaliação real e reativar CI.

1. Fase 3: tornar ingestão idempotente e rastreável.

1. Fase 4: criar modelo jurídico versionado.

1. Fase 5: corrigir FTS, pgvector e contexto hierárquico.

1. Fase 6: consolidar grounding, citações e geração.

1. Fase 7: otimizar custos, latência e operação.

1. Fase 8: melhorar a experiência de auditoria jurídica.

1. Fase 9: iniciar multiusuário somente se o requisito existir.

A Fase 2 deve começar cedo, mas a baseline final só deve ser considerada confiável depois que o corpus mínimo tiver sido revisado e as fontes não verificadas estiverem fora da recuperação padrão.

---

# 8. Go/no-go para ampliar o piloto

O LicitAI não deve ser ampliado para uso com documentos sigilosos ou múltiplos usuários enquanto qualquer uma das condições abaixo for verdadeira:

- cloud proibida ainda pode ser acionada por failover, embedding, chat ou reranking;

- corpus não verificado participa da recuperação;

- citação exibida ao usuário pode ser texto livre do LLM;

- não existe registro dos dispositivos usados na resposta;

- a busca padrão retorna redação histórica como vigente;

- o CI não executa testes críticos;

- não existe amostra jurídica revisada;

- não há backup testado com restauração;

- autenticação é opcional por ausência de configuração;

- o sistema depende de token compartilhado para uma operação multiusuário.

Para sair do piloto local, exigir pelo menos:

1. conclusão das Fases 0A, 0B, 0C, 1, 2, 3 e 4;

1. critérios de sigilo, autenticidade de citação, versionamento e rastreabilidade atendidos;

1. avaliação sem regressão acima da tolerância;

1. revisão jurídica do corpus mínimo;

1. CI ativo;

1. backup e restauração testados;

1. revisão dos riscos residuais por responsável técnico.

---

# 9. Próximas cinco ações

1. Criar a branch `fix/seguranca-sigilo-auth`.

1. Implementar a Fase 0A sem alterar o modelo jurídico.

1. Colocar o corpus TCU não verificado em quarentena.

1. Confirmar no PostgreSQL o tipo da coluna vetorial, os índices e o plano de execução.

1. Criar o primeiro conjunto curado de avaliação com perguntas sobre artigos, vigência, exceções e ausência de evidência.

A próxima implementação recomendada é exclusivamente a **Fase 0A — Bloqueio de vazamento de sigilo**. Ela tem escopo controlado, alto impacto e deve ser concluída antes de qualquer expansão do piloto.

---

## Referências

[1]: https://cursor.com/docs/models-and-pricing "Cursor Models & Pricing"

[2]: https://cursor.com/docs/models/claude-opus-5-5 "Claude Opus 5.5 no Cursor"

[3]: https://cursor.com/docs/models/grok-4-7 "Grok 4.7 no Cursor"

[4]: https://www.postgresql.org/docs/current/textsearch.html "PostgreSQL Full Text Search"

[5]: https://github.com/pgvector/pgvector "pgvector"

**Nota:** os achados específicos do repositório, os nomes de arquivos e as linhas citadas neste plano foram extraídos da auditoria anexada nesta conversa. Eles devem ser reconfirmados pelo agente no worktree antes de cada implementação.
