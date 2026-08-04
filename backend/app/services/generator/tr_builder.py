"""
Engine de Construção Assistida de Termos de Referência (TR Builder).
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentItem
from app.schemas.generator import TRGeneratorRequest, TRGeneratorResponse, TRGeneratorItemResponse
from app.services.llm.provider import get_llm_provider
from app.services.rag.retriever import retrieve
from app.services.analyzer.json_utils import parse_json_response

logger = logging.getLogger(__name__)

TIPO_ROTULOS = {
    "servicos_continuados": "Serviços Contínuos",
    "obras_engenharia": "Obras e Serviços de Engenharia",
    "tecnologia_informacao": "Tecnologia da Informação e Comunicação",
    "compras_gerais": "Aquisição de Bens / Compras Gerais",
}

CRITERIO_ROTULOS = {
    "menor_preco": "Menor Preço",
    "maior_desconto": "Maior Desconto",
    "tecnica_preco": "Técnica e Preço",
}


async def generate_tr_document(
    request: TRGeneratorRequest,
    db: AsyncSession,
) -> TRGeneratorResponse:
    """
    Gera um Termo de Referência completo estruturado sob o Art. 6º, XXIII da Lei 14.133/21,
    consultando a base de jurisprudência do TCU e RILC CODEBA.
    """
    provider = get_llm_provider()

    # 1. Recuperar contexto jurídico no RAG para o objeto
    query_rag = f"Termo de Referência {request.tipo_contratacao} {request.objeto}"
    chunks = await retrieve(db, query_rag, top_k=3)
    rag_context = "\n\n".join([f"[{c.law_number} - {c.article}]\n{c.text}" for c in chunks])

    system_prompt = """Você é um especialista em Contratações Públicas e Redação de Termos de Referência (Lei 14.133/2021, Lei 13.303/2016 e TCU).

Sua tarefa é GERAL O TEXTO COMPLETO E ESTRUTURADO DE UM TERMO DE REFERÊNCIA com as 10 seções obrigatórias do Art. 6º, XXIII:
1. DO OBJETO
2. DA JUSTIFICATIVA DA CONTRATAÇÃO
3. DAS ESPECIFICAÇÕES TÉCNICAS E REQUISITOS DA CONTRATAÇÃO
4. DO MODELO DE EXECUÇÃO DO CONTRATO
5. DO MODELO DE GESTÃO E FISCALIZAÇÃO CONTRATUAL
6. DOS CRITÉRIOS DE MEDIÇÃO E PAGAMENTO
7. DA ESTIMATIVA DE PREÇOS E ADEQUAÇÃO ORÇAMENTÁRIA
8. DA GARANTIA CONTRATUAL E ASSISTÊNCIA TÉCNICA
9. DAS INFRAÇÕES E SANÇÕES ADMINISTRATIVAS
10. DA FORMA DE SELEÇÃO E CRITÉRIO DE JULGAMENTO

## REGRAS DE SAÍDA (EXCLUSIVAMENTE JSON):
Retorne a saída estritamente em formato JSON com o seguinte formato:
{
  "secoes": [
    {
      "item_number": "1.0",
      "title": "DO OBJETO",
      "content": "Texto detalhado da seção..."
    },
    ...
  ]
}
"""

    valor_txt = f"R$ {request.valor_estimado:,.2f}" if request.valor_estimado else "A definir em pesquisa de mercado"
    tipo_nome = TIPO_ROTULOS.get(request.tipo_contratacao, request.tipo_contratacao)
    criterio_nome = CRITERIO_ROTULOS.get(request.criterio_julgamento, request.criterio_julgamento)

    user_prompt = f"""GERAR TERMO DE REFERÊNCIA COMPLETO:

## Parâmetros da Contratação:
- **Tipo de Contratação:** {tipo_nome}
- **Objeto:** {request.objeto}
- **Justificativa:** {request.justificativa}
- **Valor Estimado Global:** {valor_txt}
- **Vigência Contratual:** {request.prazo_meses} meses
- **Exigência de Garantia:** {"Sim" if request.garantia_exigida else "Não"}
- **Exigência de Vistoria Técnica:** {"Sim" if request.vistoria_exigida else "Não"}
- **Critério de Julgamento:** {criterio_nome}

## Jurisprudência e Normas Relevantes (RAG):
{rag_context if rag_context else "Lei 14.133/2021 e normas aplicáveis."}

Gere o JSON com todas as 10 seções completas, com linguagem jurídica formal, objetiva e sem cláusulas vazias.
"""

    raw_response = await provider.generate(system_prompt, user_prompt)
    data = parse_json_response(raw_response)

    secoes_json = data.get("secoes", []) if isinstance(data, dict) else []

    # Fallback se a LLM não retornar estrutura válida
    if not secoes_json:
        secoes_json = [
            {"item_number": "1.0", "title": "DO OBJETO", "content": f"O objeto da presente contratação consiste em: {request.objeto}"},
            {"item_number": "2.0", "title": "DA JUSTIFICATIVA DA CONTRATAÇÃO", "content": request.justificativa},
            {"item_number": "3.0", "title": "DAS ESPECIFICAÇÕES TÉCNICAS E REQUISITOS DA CONTRATAÇÃO", "content": f"Os serviços/bens deverão atender aos requisitos mínimos para contratação de {tipo_nome}."},
            {"item_number": "4.0", "title": "DO MODELO DE EXECUÇÃO DO CONTRATO", "content": f"O prazo de execução/vigência do contrato será de {request.prazo_meses} meses."},
            {"item_number": "5.0", "title": "DO MODELO DE GESTÃO E FISCALIZAÇÃO CONTRATUAL", "content": "A fiscalização do contrato será exercida por comissão/fiscal designado conforme normas internas."},
            {"item_number": "6.0", "title": "DOS CRITÉRIOS DE MEDIÇÃO E PAGAMENTO", "content": "O pagamento será efetuado mediante liquidação da nota fiscal/fatura emitida pela contratada."},
            {"item_number": "7.0", "title": "DA ESTIMATIVA DE PREÇOS E ADEQUAÇÃO ORÇAMENTÁRIA", "content": f"Valor estimado global: {valor_txt}."},
            {"item_number": "8.0", "title": "DA GARANTIA CONTRATUAL E ASSISTÊNCIA TÉCNICA", "content": "Exigência de garantia contratual: " + ("Sim, no percentual de 5%." if request.garantia_exigida else "Isento de garantia.")},
            {"item_number": "9.0", "title": "DAS INFRAÇÕES E SANÇÕES ADMINISTRATIVAS", "content": "Aplica-se ao presente contrato o regime de sanções previsto nos Arts. 155 e seguintes da Lei 14.133/2021."},
            {"item_number": "10.0", "title": "DA FORMA DE SELEÇÃO E CRITÉRIO DE JULGAMENTO", "content": f"A seleção do fornecedor dar-se-á por licitação na modalidade Pregão/Concorrência pelo critério de {criterio_nome}."},
        ]

    # 2. Persistir no banco de dados como um novo Document
    doc_id = uuid.uuid4()
    nome_arquivo = f"TR_Gerado_{request.tipo_contratacao}_{doc_id.hex[:6]}.html"

    doc = Document(
        id=doc_id,
        filename_original=f"Termo de Referência — {tipo_nome}",
        filename_stored=nome_arquivo,
        file_type="docx",
        file_size_bytes=len(raw_response.encode("utf-8")),
        document_type="tr",
        total_items=len(secoes_json),
        status="parsed",
    )
    db.add(doc)

    items_res: list[TRGeneratorItemResponse] = []
    html_parts = [f"<h1>TERMO DE REFERÊNCIA — {tipo_nome.upper()}</h1>\n"]

    for idx, sec in enumerate(secoes_json):
        num = sec.get("item_number", f"{idx+1}.0")
        tit = sec.get("title", f"SEÇÃO {idx+1}")
        cnt = sec.get("content", "")

        doc_item = DocumentItem(
            id=uuid.uuid4(),
            document_id=doc_id,
            item_number=num,
            title=tit,
            content=cnt,
            page_number=1,
            item_order=idx + 1,
            item_type="section",
        )
        db.add(doc_item)

        items_res.append(TRGeneratorItemResponse(item_number=num, title=tit, content=cnt))
        html_parts.append(f"<h2>{num} {tit}</h2>\n<p>{cnt.replace('\n', '<br/>')}</p>\n")

    await db.commit()
    await db.refresh(doc)

    return TRGeneratorResponse(
        document_id=doc_id,
        filename_original=doc.filename_original,
        tipo_contratacao=request.tipo_contratacao,
        total_itens=len(items_res),
        html_completo="".join(html_parts),
        itens=items_res,
    )
