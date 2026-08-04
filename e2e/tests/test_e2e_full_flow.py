import pytest


class TestHealth:
    def test_health_check(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["provider"] in ("groq", "gemini", "ollama")


class TestUpload:
    def test_upload_docx(self, api_client, sample_docx_path):
        with open(sample_docx_path, "rb") as f:
            response = api_client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "sample-tr.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["filename_original"] == "sample-tr.docx"
        assert data["file_type"] in (".docx", "docx")
        assert data["status"] in ("parsed", "parsing", "error")
        assert "id" in data

    def test_upload_invalid_extension(self, api_client):
        response = api_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"conteudo invalido", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_empty_filename(self, api_client):
        response = api_client.post(
            "/api/v1/documents/upload",
            files={"file": ("", b"", "application/octet-stream")},
        )
        assert response.status_code in (400, 422)


class TestDocumentLifecycle:
    def test_list_documents(self, api_client, uploaded_document):
        response = api_client.get("/api/v1/documents/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        ids = [d["id"] for d in data["documents"]]
        assert uploaded_document["id"] in ids

    def test_get_document(self, api_client, uploaded_document):
        doc_id = uploaded_document["id"]
        response = api_client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["status"] in ("parsed", "completed")
        assert len(data["items"]) > 0

    def test_get_document_not_found(self, api_client):
        import uuid
        fake_id = uuid.uuid4()
        response = api_client.get(f"/api/v1/documents/{fake_id}")
        assert response.status_code == 404

    def test_delete_document(self, api_client, uploaded_document):
        doc_id = uploaded_document["id"]
        response = api_client.delete(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 204

        response = api_client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 404


class TestAnalysis:
    def test_start_analysis(self, api_client, uploaded_document):
        doc_id = uploaded_document["id"]
        response = api_client.post(f"/api/v1/analysis/{doc_id}/start")
        assert response.status_code == 202
        data = response.json()
        assert "analysis_id" in data
        assert data["message"] == "Análise iniciada. Acompanhe o progresso pelo endpoint de status."

    def test_start_analysis_document_not_found(self, api_client):
        import uuid
        fake_id = uuid.uuid4()
        response = api_client.post(f"/api/v1/analysis/{fake_id}/start")
        assert response.status_code == 404

    def test_analysis_completes_with_corrections(self, api_client, analyzed_document):
        analysis = analyzed_document["analysis"]
        assert analysis["status"] == "completed"
        assert analysis["analyzed_items"] >= 1
        assert len(analysis["corrections"]) >= 1
        correction = analysis["corrections"][0]
        assert correction["category"] in ("juridica", "tecnica", "redacao", "estrutural")
        assert correction["original_text"]
        assert correction["suggested_text"]
        assert correction["justification"]

    def test_analysis_has_scores(self, api_client, analyzed_document):
        analysis = analyzed_document["analysis"]
        assert analysis["score_overall"] is not None

    def test_analysis_has_risk_level(self, api_client, analyzed_document):
        analysis = analyzed_document["analysis"]
        assert analysis["risk_level"] in ("baixo", "medio", "alto", "critico")


class TestReport:
    def test_get_report(self, api_client, analyzed_document):
        analysis_id = analyzed_document["analysis_id"]
        response = api_client.get(f"/api/v1/analysis/{analysis_id}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == analysis_id
        assert data["status"] == "completed"
        assert len(data["scores"]) == 5
        assert data["risk_level"] is not None
        assert data["total_corrections"] >= 1
        assert data["final_opinion"] is not None
        assert data["analyzed_at"] is not None

        for score in data["scores"]:
            assert "label" in score
            assert "score" in score

    def test_report_has_document_name(self, api_client, analyzed_document):
        analysis_id = analyzed_document["analysis_id"]
        response = api_client.get(f"/api/v1/analysis/{analysis_id}/report")
        data = response.json()
        assert data["document_name"] == "sample-tr.docx"

    def test_report_not_found(self, api_client):
        import uuid
        fake_id = uuid.uuid4()
        response = api_client.get(f"/api/v1/analysis/{fake_id}/report")
        assert response.status_code == 404

    def test_list_document_analyses(self, api_client, analyzed_document):
        doc_id = analyzed_document["document"]["id"]
        response = api_client.get(f"/api/v1/analysis/document/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["document_id"] == doc_id
