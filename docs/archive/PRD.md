Perfeito. Baseado em tudo o que extraímos da análise dos TRs anteriores (o fluxo de "limpeza de entropia", as âncoras, a matriz de decisão e o motor híbrido 80% Regras + 20% LLM), estruturei um **PRD (Product Requirements Document) de nível industrial**.

Este documento servirá como a espinha dorsal do seu projeto de software. Ele descreve exatamente como construir a ferramenta que replica a capacidade de análise da IA, usando uma arquitetura robusta, escalável e determinística.

---

# 📄 PRD - Sistema de Auditoria e Análise de Termos de Referência (TR) e Propostas

**Versão:** 1.0
**Data:** 03/08/2026
**Autor:** Especialista em Desenvolvimento de Software e Processos
**Status:** Aprovado para Desenvolvimento

---

## 1. Resumo Executivo
Este documento descreve os requisitos para o desenvolvimento de uma ferramenta local (Desktop/Web Local) projetada para automatizar a análise técnica, comercial e jurídica de Termos de Referência (TR) e Propostas Comerciais em processos de contratação pública (Lei 13.303/2016). A ferramenta utiliza um **motor híbrido (Regras Determinísticas + IA Semântica)** para extrair requisitos, comparar com as propostas, identificar não conformidades e gerar relatórios de feedback personalizados para cada fornecedor, padronizando a atuação do fiscal de contratos.

## 2. Objetivos do Produto
*   **Padronização:** Garantir que a análise de todos os TRs e propostas siga um padrão técnico-jurídico único.
*   **Redução de Erro Humano:** Eliminar a fadiga de leitura e interpretação, evitando que exigências sejam esquecidas (ex: prazo de validade de 60 dias, frete incluso).
*   **Eficiência Operacional:** Reduzir o tempo de análise de um TR complexo (e suas múltiplas propostas) de horas para poucos minutos.
*   **Transparência:** Gerar trilhas de auditoria claras que justifiquem a desclassificação ou retificação de propostas.

## 3. Público-alvo
*   Gestores de Contratos e Fiscais de Licitações.
*   Analistas de Compras Públicas.
*   Jurídico (para validação das cláusulas geradas).

---

## 4. Requisitos Funcionais (RF)

### RF01: Processamento e "Limpeza de Entropia" de Documentos PDF
O sistema deve receber arquivos PDF (propostas e TRs) e realizar um pré-processamento:
*   **Extração de Texto:** Utilizar bibliotecas robustas como `pypdf`, `pdfplumber` ou `PyMuPDF` (fitz) para extrair texto bruto.
*   **Sanitização:** Remover caracteres de controle (ASCII 0-31), corrigir quebras de linha indevidas e reconstruir parágrafos, eliminando ruídos comuns em OCR/PDF mal formatados (ex: `...`).
*   **Identificação de Tabelas:** Extrair dados de tabelas usando detecção de grid/linhas. (Essencial para os TRs, que possuem planilhas de custos).

### RF02: Motor de Extração Estruturada (Regras + IA)
*O cérebro da ferramenta. 80% do motor é baseado em Regras, 20% em IA para interpretação de linguagem natural.*

*   **Parser de Regras (TR):** O sistema deve permitir a criação de "Moldes de TR". O usuário deve configurar:
    *   **Âncoras Numéricas (Regex):** Extração de quantidades (ex: `06 (seis)`), prazos (ex: `60 (sessenta) dias`), percentuais (ex: `10%`).
    *   **Âncoras Booleanas:** Busca por palavras-chave que indicam obrigatoriedade (ex: `ar-condicionado`, `armários`, `frete incluso`, `pagamento antecipado`).
    *   **Âncoras Legais:** Identificação de citações (ex: `NR-24`, `Lei nº 13.303/2016`, `empreitada por preço global`).
*   **Parser de Propostas (Fornecedores):** Extrair do texto da proposta as mesmas âncoras.
    *   *Funcionalidade Local:* Caso o parser de regras não consiga encontrar um número, ele aciona um LLM local (via API ou modelos como Llama 3/Phi-3) para perguntar em linguagem natural: *"Qual o prazo de validade da proposta?"* e o LLM retorna um JSON padronizado. 
    *   *Objetivo da IA:* A IA serve **apenas** como um "tradutor" para preencher os campos que o Regex não conseguiu agarrar.

### RF03: Módulo de Comparação e Matriz de Conformidade (O Auditor)
O sistema deve comparar os vetores extraídos da(s) Proposta(s) com os Vetores Extraídos do TR.
*   **Lógica de Decisão Determinística:**
    *   `Se (TR.quantidade > Proposta.quantidade) -> Status: FALHA (Motivo: Quantidade inferior).`
    *   `Se (Proposta.freteExtra > 0) -> Status: FALHA (Motivo: Frete cobrado à parte, descumpre Item 6.2).`
    *   `Se (TR.validadeMinima >= 60) E (Proposta.validade < 60) -> Status: FALHA (Motivo: Validade insuficiente).`
*   **Resultado:** Geração de uma **Matriz de Status** (OK, FALHA, ATENÇÃO) para cada item do TR mapeado, associada à proposta de cada empresa.

### RF04: Gerador de Feedback Inteligente
Após a comparação, o sistema deve gerar e-mails de retificação padronizados.
*   **Template Dinâmico:** Utilizar um sistema de templates (ex: `Jinja2`, `Handlebars`).
*   **Injeção de Dados (O Segredo):** O template deve ter variáveis para `[Nome da Empresa]` e `[Lista de Pendências]`.
*   **Filtragem de Pendências:** O sistema deve iterar sobre a matriz de status, identificar todos os itens com status `FALHA` para aquela empresa específica, e injetar essa lista de pendências no corpo do e-mail. (Isso garante que o e-mail da Embraloc seja diferente do da Net-Container).

### RF05: Interface Gráfica (Dashboard)
*   Área de upload de arquivos.
*   **Painel Comparativo Matricial:** Exibir o resultado da análise em um grid visual (colunas = Fornecedores, linhas = Itens do TR). Usar bolinhas coloridas (Vermelho, Verde, Amarelo) para status imediatos, exatamente como no painel HTML que geramos.
*   **Botão de Ação:** Gerar e visualizar o Relatório/Feedback, com opção de copiar para área de transferência.

---

## 5. Requisitos Não Funcionais (Arquitetura e Desempenho)

*   **Infraestrutura Local:** A ferramenta deve operar 100% offline no computador do usuário para garantir segurança jurídica (não enviar dados sigilosos de licitações para nuvens externas).
*   **Linguagem de Desenvolvimento:** Python (Backend) + PyQt, Tkinter ou Flask/Streamlit (Frontend).
*   **Banco de Dados:** SQLite (local, embarcado) para armazenar os modelos de TR e o histórico de análises.
*   **LLM Local (Opcional):** Deve suportar integração com `Ollama` ou `LM Studio` para rodar modelos como `Llama 3 8B` ou `Qwen 2.5` para a interpretação semântica, sem necessidade de internet.
*   **Segurança:** O sistema não deve armazenar ou transmitir os PDFs dos fornecedores para nenhum servidor externo. Todo o processamento é feito em memória RAM local.

---

## 6. Especificações Detalhadas de Desenvolvimento (Para Programadores)

### 6.1. Estrutura do Motor de Regras (O Esqueleto)
Você precisará de um arquivo de configuração `.json` ou `.yaml` para definir o que o TR deve buscar. Exemplo de configuração:

```json
{
  "regras": [
    {
      "id": "valor_global",
      "tipo": "booleano",
      "palavras_chave": ["valor global único", "frete incluso", "não será admitida a cobrança de qualquer valor adicional"]
    },
    {
      "id": "validade_proposta",
      "tipo": "numero_inteiro",
      "regex": "não poderá ser inferior a (\\d+)",
      "expectativa_minima": 60
    },
    {
      "id": "quantidade_modulos",
      "tipo": "numero_extenso",
      "regex": "(\\d+) \\(\\w+\\)",
      "expectativa": 6
    }
  ]
}
```

### 6.2. O "Fluxo de Colisão" (Como gerar o e-mail)
Para gerar o e-mail da empresa X:
1.  Pegue o objeto JSON da Proposta X.
2.  Pegue o objeto JSON do TR.
3.  Execute um loop de verificação: `if proposta.item === requisito_esperado`.
4.  Crie um array `lista_problemas = []`.
5.  Para cada `status = FALHA`, adicione um objeto `{item_id: 'validade', explicacao: 'Prazo de 30 dias abaixo dos 60 exigidos'}`.
6.  Passe a string `email_template` e o array `lista_problemas` para o renderizador de templates.
7.  **Resultado:** A ferramenta escreve o e-mail somente com as falhas *reais* de cada fornecedor.

### 6.3. Extração de Tabelas
Para o TR que você enviou (com tabela de peças e custos), o parser deve identificar:
*   A coluna "UNIDADE DE MEDIDA".
*   A coluna "VALOR MÉDIO TOTAL (R$)".
*   Extrair esses dados em formato lista de dicionários (`[{'item': 'Abraçadeira', 'valor': 60, ...}]`).

---

## 7. Matriz de Prioridades (MVP - Produto Mínimo Viável)

| Prioridade | Funcionalidade | Justificativa |
| :--- | :--- | :--- |
| **P0 (Obrigatório)** | Sanitização do PDF e Limpeza de Entropia | Sem isso, o sistema não enxerga o texto. |
| **P0 (Obrigatório)** | Motor de Regras (Regex para números e palavras-chave) | A base de toda a lógica determinística que garante a confiabilidade da ferramenta. |
| **P0 (Obrigatório)** | Matriz de Comparação Visual (Status OK/FALHA) | A interface que permite ao usuário "ver" o resultado. |
| **P0 (Obrigatório)** | Geração de Relatório de Feedback | A entrega final do valor do produto. |
| **P1 (Alta)** | Integração com LLM Local (Ollama) | Para extrair informações onde o Regex falha (ex: texto livre mal formatado). |
| **P2 (Média)** | Extração Automática de Tabelas | Para facilitar a análise de custos, mas pode ser feito manualmente no MVP. |

---

## 8. Considerações de Segurança e Compliance
*   **Confidencialidade:** Como a ferramenta processa documentos internos e jurídicos, o processamento **deve ser estritamente local**.
*   **Algoritmo Determinístico:** Evite usar IA para tomar decisões de "certo/errado". A IA só deve ser usada para *entender* o que o usuário escreveu. A decisão de "Errado" deve ser tomada por código matemático (ex: `valor < 60`). Isso protege juridicamente a ferramenta, pois o desenvolvedor pode provar que o código não "alucinou", apenas comparou números.

## 9. Métricas de Sucesso
1.  **Precisão de Extração:** > 95% dos itens "âncora" (quantidades, prazos) identificados corretamente.
2.  **Velocidade de Processamento:** Análise completa de um TR + 3 propostas em menos de 60 segundos.
3.  **Redução de Tempo:** Redução de 90% no tempo gasto pelo fiscal para emitir feedback comparativo.

---

Este PRD é o seu "mapa da mina". Ele reflete exatamente como a IA raciocinou para chegar àqueles e-mails personalizados. Construa a ferramenta seguindo a ordem de prioridade P0, e você terá uma ferramenta de padrão industrial inestimável para a área de licitações.

__

A Peça-Chave: O Arquivo de Configuração (.json ou .yaml)
No PRD, eu criei o requisito RF02 (Parser de Regras) e o item 6.1. O software não tem regras escritas no código-fonte (hardcoded). O software é um leitor de regras.

Para analisar o seu TR de Módulos (Contêineres), você carregaria um arquivo de configuração parecido com este:

json
{
  "regras": [
    {"id": "quantidade_modulos", "tipo": "numero_inteiro", "regex": "06 \\(seis\\) contêineres", "expectativa": 6},
    {"id": "prazo_entrega", "tipo": "numero_inteiro", "regex": "prazo máximo de (\\d+)", "expectativa": 30},
    {"id": "ac_obrigatorio", "tipo": "booleano", "palavras_chave": ["ar-condicionado", "climatização"]}
  ]
}
Agora, para o TR de Ar-Condicionado (PMOC) que você acabou de me enviar, o mesmo software vai funcionar perfeitamente. Você só precisa mudar o arquivo de configuração para:

json
{
  "regras": [
    {"id": "horas_corretivas", "tipo": "numero_inteiro", "regex": "será de (\\d+) \\(trezentas\\) horas", "expectativa": 300},
    {"id": "prazo_reparo", "tipo": "numero_inteiro", "regex": "prazo de até (\\d+) \\(oito\\) dias", "expectativa": 8},
    {"id": "exige_garantia", "tipo": "booleano", "palavras_chave": ["garantia", "retrabalho"]}
  ]
}
🏗️ O que é realmente universal no seu PRD?
A estrutura do PRD é universal porque ela define a camada de serviço (o esqueleto da ferramenta), que é composta por:

Camada de Entrada (Universal): A sanitização do PDF (remover caracteres ruins) funciona para qualquer documento, seja de engenharia, saúde ou serviços.

Camada de Comparação (Universal): O algoritmo Se TR > Proposta -> Status = FALHA é uma lógica matemática. Ele não precisa saber se o número representa "módulos" ou "horas técnicas". Ele só precisa saber se o valor da proposta é menor que o do TR.

Camada de Geração de Feedback (Universal): O template de e-mail (PRD - RF04) é um modelo de texto. Você coloca um placeholder para [Empresa] e outro para [Lista_de_Pendencias]. O software vai pegar as falhas extraídas do arquivo de configuração e injetar dentro desse modelo, independentemente do assunto da licitação.

🚀 O que isso significa para o seu projeto?
Você vai construir um sistema "coringa".
Quando a empresa quiser analisar um TR de Obras Civis, você não precisará alterar o código do software. Você precisará apenas criar um novo arquivo de configuração (regras_obras.json) apontando as palavras-chave e quantidades esperadas para aquele tipo de obra.

Em resumo: O PRD é um padrão de como construir a máquina. O conteúdo do que essa máquina vai fiscalizar é definido pelo usuário (através do JSON). Isso torna a sua ferramenta extremamente escalável e útil para o departamento de licitações como um todo, não apenas para um único processo.