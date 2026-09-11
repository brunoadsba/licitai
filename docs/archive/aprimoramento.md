# Ferramentas 100% Open-Source e Gratuitas para o LicitAI

Com base na sua exigência de ferramentas **100% Free e Open-Source (FOSS)**, selecionei os projetos que você pode clonar, modificar e integrar ao seu backend (FastAPI) e banco de dados (PostgreSQL/pgvector) sem custos de licença ou dependência de serviços fechados.

---

## 1. Licinexus MCP (MIT License)

Este é o projeto mais valioso para o seu LicitAI. Ele é totalmente aberto e resolve o problema de conexão com dados públicos.

- **Como usar no seu projeto:** Em vez de usar como um "servidor" separado, você pode extrair a lógica dos **adaptadores de API** que eles construíram para o PNCP e BrasilAPI.

- **Utilidade:** No seu módulo `services/analyzer`, você pode incluir uma função que consulta o PNCP para verificar se o objeto do seu TR tem preços de referência compatíveis com atas de registro de preços vigentes.

- **Link:** [github.com/Licinexus/licinexus-mcp](https://github.com/Licinexus/licinexus-mcp)

## 2. Farol - Radar de Contratos (GPL-3.0 License)

O Farol é 100% open-source e focado em transparência pública.

- **Como usar no seu projeto:** O Farol possui um diretório chamado `packages/api/src/modules/anomalies`. Lá, eles têm algoritmos prontos (em TypeScript, mas facilmente portáveis para o seu Python/FastAPI) que definem regras de risco para licitações.

- **Utilidade:** Você pode "importar" a lógica de cálculo de score de risco deles para o seu `services/analyzer/engine.py`, permitindo que o LicitAI identifique não só erros de texto, mas anomalias estruturais e de competitividade.

- **Link:** [github.com/luansievers/farol](https://github.com/luansievers/farol)

## 3. Datasets de Treinamento e RAG (Hugging Face - Open Data)

Os datasets abaixo são distribuídos sob licenças abertas (como Creative Commons) e são essenciais para o seu módulo `services/rag` que está em construção.

- **JurisTCU (LeandroRibeiro):** Contém milhares de acórdãos e súmulas do TCU. Você pode baixar os arquivos `.parquet` ou `.json` e injetar diretamente no seu `pgvector`. Isso dará ao seu LicitAI a capacidade de citar jurisprudência real para justificar as correções.

- **BidCorpus (TCE-PI):** Dataset específico sobre editais. Útil para você testar a precisão do seu `parser` e do seu `analyzer` contra documentos reais já validados por tribunais de contas.

## 4. Gerador de Documentos (Murilo Locatti - MIT/Open)

Embora simples, o código é 100% aberto e focado na Lei 14.133/2021.

- **Como usar no seu projeto:** Se você precisar de modelos (templates) estruturados de TR, ETP e DFD para oferecer como sugestão de "PARA" no seu sistema, o código dele contém as estruturas de campos obrigatórios da nova lei mapeadas em HTML/JS que você pode converter para seus modelos de dados.

- **Link:** [github.com/locattimurilo/geradordedocumentos](https://github.com/locattimurilo/geradordedocumentos)

---

## Resumo de Integração Técnica para o LicitAI

| Componente LicitAI | Ferramenta FOSS Sugerida | Ação Recomendada |
| --- | --- | --- |
| **services/rag** | `JurisTCU` (Dataset) | Ingerir os chunks de jurisprudência no seu `pgvector`. |
| **services/analyzer** | `Farol` (Lógica) | Portar as regras de anomalia (risco) para Python. |
| **services/parser** | `BidCorpus` (Dataset) | Usar os documentos para validar seu extrator de texto. |
| **Market Context** | `Licinexus` (Adaptadores) | Usar o código de integração com o PNCP para buscar preços. |

Essas ferramentas garantem que seu projeto continue sendo um software soberano, sem taxas de API de terceiros (além dos provedores de LLM que você já escolheu) e com total controle sobre o código-fonte.