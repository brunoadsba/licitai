"""
Régua de regressão Fase 0 — 11 achados congelados de afd39876 (TR 09-ti-pabx-nuvem).

Precisão humana 0.09-0.18 (9 rejeitadas, 1 aprovada, 1 ajustada).
Cada caso: item real (simplificado) + achado + veredito esperado do gate.
O teste FALHA com gate desligado (prova que a fase morde FP) e PASSA ligado.
"""

from app.services.analyzer.evidence_gate import detect_regime, evaluate_finding

DOC_RILC = (
    "COMPANHIA DE DOCAS DO ESTADO DA BAHIA CODEBA RILC "
    "Lei 13.303/2016 estatal regulamento interno "
    "1.4 vigencia 24 meses 4.3.2 130 ramais 11.5 prorrogacao "
    "Acordao TCU 1214/2013 Sumula 247"
)

ITEM_11 = "1.1 Objeto contratacao de solucao de pabx em nuvem com suporte tecnico"


def _corr(**kw):
    base = {
        "category": "tecnica",
        "severity": "medio",
        "situation": "",
        "problem": "",
        "risk": "",
        "original_text": "",
        "suggested_text": "",
        "justification": "",
        "legal_basis": None,
        "importance": "media",
    }
    base.update(kw)
    return base


def test_g1_trecho_rag_nao_barrava_sem_gate():
    # [0] trecho do RAG passado por texto do item
    c = _corr(
        original_text="conforme Acordao TCU a competitividade exige parcelamento do objeto",
        suggested_text="parcelar o objeto",
        problem="falta parcelamento",
    )
    # Sem gate: grounding exato antigo deixava passar? Aqui documentamos que
    # o achado EXISTIA (era persistido). Com gate: G1 reprova.
    r = evaluate_finding(c, ITEM_11, DOC_RILC)
    assert not r.passed and r.gate == "G1"


def test_g2_numeros_inventados():
    # [4] 30%/15%/20% fabricados
    c = _corr(
        original_text="multa por inadimplemento",
        suggested_text="aplicar multa de 30% e juros de 15% com desconto de 20%",
        problem="penalidade indefinida",
    )
    # item contém o trecho para passar G1, mas números não existem no doc
    r = evaluate_finding(c, "multa por inadimplemento contratual", "doc sem numeros relevantes")
    assert not r.passed and r.gate == "G2"


def test_g4_omissao_desmentida_11():
    # [10] 1.1 "sem prazo" quando 1.4 tem 24 meses e 11.5 prorrogacao
    c = _corr(
        original_text="",
        suggested_text="definir vigencia de 24 meses com prorrogacao",
        problem="nao especifica o prazo de vigencia do contrato",
        legal_basis="Lei 14.133/2021, art. 6",
    )
    r = evaluate_finding(c, ITEM_11, DOC_RILC)
    assert not r.passed and r.gate in ("G3", "G4")  # regime ou busca doc-wide


def test_g3_lei_fora_do_regime():
    for idx in ("[2]", "[7]"):
        c = _corr(
            original_text="contratacao de servico continuado",
            suggested_text="adequar ao art. 6 da Lei 14.133",
            problem=f"{idx} fundamento incorreto",
            legal_basis="Lei 14.133/2021, art. 6",
        )
        r = evaluate_finding(
            c, "contratacao de servico continuado estatal", DOC_RILC
        )
        assert not r.passed and r.gate == "G3", idx


def test_g2_placeholder_xyz():
    c = _corr(
        original_text="prazo de entrega",
        suggested_text="entregar em X dias no local Y pelo valor Z",
        problem="prazo indefinido",
    )
    r = evaluate_finding(c, "prazo de entrega do equipamento", DOC_RILC)
    assert not r.passed and r.gate == "G2"


def test_ops_ruido_operacional():
    for i in (1, 3, 5, 8):
        c = _corr(
            category="tecnica",
            severity="alto",
            original_text="",
            suggested_text="",
            problem="Reexecutar a analise do item: falha de cobertura",
        )
        r = evaluate_finding(c, "qualquer item", DOC_RILC)
        assert not r.passed and r.gate == "OPS", f"[{i}]"


def test_g1_fatia_truncada():
    # [6]/[9] defeito era artefato de segmentacao
    c = _corr(
        original_text="solucao de pabx em nuvem com suporte tecnico especializado e treinamento",
        suggested_text="detalhar escopo",
        problem="escopo incompleto",
    )
    r = evaluate_finding(c, "trecho totalmente diferente sobre medicao e pagamento", DOC_RILC)
    assert not r.passed and r.gate == "G1"


def test_tp_real_passa():
    c = _corr(
        category="juridica",
        severity="medio",
        original_text="contratacao de servico continuado",
        suggested_text="incluir criterio de medicao e pagamento mensal detalhado",
        problem="criterio de medicao vago, detalhar periodicidade",
        legal_basis="Acordao TCU 1214/2013",
    )
    r = evaluate_finding(
        c, "contratacao de servico continuado com medicao vaga", DOC_RILC
    )
    assert r.passed and r.gate == "OK"


def test_detect_regime_rilc():
    assert detect_regime(DOC_RILC) == "13.303"
    assert detect_regime("pregao eletronico Lei 14.133/2021 entes federativos") == "14.133"
    assert detect_regime("texto neutro sem sinais") is None


def test_claim_support_rate():
    from app.services.analyzer.evidence_gate import claim_support_rate

    bom = _corr(
        original_text="prazo de vigência",
        suggested_text="prazo de vigência de 24 meses",
        problem="prazo vago",
        legal_basis="Acordao TCU 1214/2013",
    )
    r = claim_support_rate(bom, "prazo de vigência contratual", "vigência 24 meses")
    assert r["supported"] == r["total"]

    ruim = _corr(
        original_text="multa",
        suggested_text="multa de 30%",
        problem="indefinido",
    )
    r2 = claim_support_rate(ruim, "multa contratual", "doc sem numeros")
    assert r2["supported"] < r2["total"]
