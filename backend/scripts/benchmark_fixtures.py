"""
Fixtures para o benchmark de qualidade da análise (Fase 2.3).

TRs com problemas conhecidos e respostas esperadas (palavras-chave por item).
O contexto jurídico fixo simula o RAG de forma determinística para o benchmark.
"""

LEGAL_CONTEXT = """### Lei 14.133/2021 — Art. 6º, XXIII
Termo de Referência é o documento necessário para a contratação de bens ou
serviços, que deve conter os seguintes elementos: definição do objeto com
quantidade e unidade de medida; justificativa da contratação; requisitos
técnicos mínimos; modelo de execução do contrato; modelo de gestão do contrato;
estimativa de quantidades; cronograma físico-financeiro; critérios de medição e
pagamento; sanções administrativas aplicáveis; e garantias quando exigíveis.

### Lei 14.133/2021 — Art. 92
O contrato deve conter cláusulas que estabeleçam o objeto e seus elementos
característicos; o prazo de vigência; o preço e as condições de pagamento; os
prazos de entrega; as sanções administrativas; e as condições de garantia.

### Lei 14.133/2021 — Art. 40, § 3º
Os quantitativos constantes das planilhas devem ser estimados e a definição do
objeto deve ser precisa, suficiente e clara, vedadas especificações que limitem
ou frustrem a competitividade.
"""

BENCHMARK_TRS = [
    {
        "nome": "Serviços de limpeza — omissões graves",
        "items": [
            {
                "item_number": "1",
                "title": "Objeto",
                "content": (
                    "Contratação de empresa especializada em serviços de limpeza "
                    "e conservação predial para as dependências da sede. A empresa "
                    "deverá fornecer mão de obra, materiais e equipamentos "
                    "necessários à execução dos serviços."
                ),
            },
            {
                "item_number": "2",
                "title": "Pagamento",
                "content": (
                    "O pagamento será efetuado após a emissão de nota fiscal, "
                    "mediante conferência dos serviços prestados pela fiscalização. "
                    "O prazo de pagamento será de até 30 dias após o recebimento "
                    "definitivo."
                ),
            },
        ],
        "expected": [
            {
                "item_number": "1",
                "issues": [
                    {"keyword": "cronograma", "category": "estrutural"},
                    {"keyword": "quantidade", "category": "estrutural"},
                    {"keyword": "sanções", "category": "estrutural"},
                    {"keyword": "justificativa", "category": "estrutural"},
                ],
            },
            {
                "item_number": "2",
                "issues": [
                    {"keyword": "medição", "category": "juridica"},
                    {"keyword": "cronograma", "category": "estrutural"},
                ],
            },
        ],
    },
    {
        "nome": "Câmeras de monitoramento — direcionamento",
        "items": [
            {
                "item_number": "1",
                "title": "Especificações técnicas",
                "content": (
                    "O equipamento deverá ser da marca MonitoraX, modelo VX-2000, "
                    "com resolução mínima de 8 megapixels e gravação em nuvem "
                    "exclusiva do fabricante. Nenhum outro equipamento será aceito."
                ),
            },
        ],
        "expected": [
            {
                "item_number": "1",
                "issues": [
                    {"keyword": "marca", "category": "juridica"},
                    {"keyword": "competitividade", "category": "juridica"},
                    {"keyword": "justificativa", "category": "juridica"},
                ],
            },
        ],
    },
    {
        "nome": "TR adequado — sem problemas relevantes",
        "items": [
            {
                "item_number": "1",
                "title": "Objeto e justificativa",
                "content": (
                    "Contratação de empresa para fornecimento de 500 (quinhentas) "
                    "cadeiras ergonômicas, conforme especificações técnicas do anexo. "
                    "A contratação justifica-se pela necessidade de adequação do "
                    "mobiliário às normas de ergonomia, conforme laudo técnico "
                    "anexo. O cronograma físico-financeiro consta no anexo III, "
                    "com etapas de entrega, medição e pagamento definidos."
                ),
            },
        ],
        "expected": [],
    },
]
