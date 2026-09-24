# Extensão LicitAI para o SEI

Injeta o Termo de Referência no editor do SEI. O HTML passa por sanitização (sem script, sem atributos) e o conteúdo vem do BFF do LicitAI (`http://127.0.0.1:3000/api/proxy`), que injeta o `API_TOKEN`. A extensão não guarda o token.

Prefere o endpoint `corrected-html` (já escapado no servidor). Se não houver correção aprovada, monta o texto original com escape.

## Instalar (Chrome / Edge / Brave)

1. Abra `chrome://extensions` (ou equivalente).
2. Ative o modo do desenvolvedor.
3. Carregar sem compactação: pasta `extension` deste repositório.

## Usar

1. Suba o LicitAI (`./scripts/up.sh`). A UI precisa estar em `http://127.0.0.1:3000`.
2. Abra o editor do SEI.
3. Clique no ícone da extensão e escolha o TR.
4. Recarregue a extensão depois de atualizar os arquivos desta pasta.
