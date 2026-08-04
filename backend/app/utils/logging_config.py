"""
Configuração de logging estruturado em JSON.

Formata cada registro como um objeto JSON com campos padronizados:
timestamp, level, logger, message e (opcionalmente) exc_info.

Importante: nenhum dado sensível (chaves de API, conteúdo de documentos)
é incluído. Mensagens que precisem de contexto devem usar campos extras
através do argumento `extra`.
"""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Formatter que serializa cada registro em uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """Configura o logging raiz com formatter JSON."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
