#!/bin/bash
# SessionStart hook — instala as dependências do jogo (pygame, Pillow) para que
# os testes headless em tests/ e o smoke de main_pygame rodem em sessões web.
# Síncrono e idempotente; só faz trabalho no ambiente remoto (Claude on the web).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

# SDL sem janela: garante que pygame inicialize headless nos testes/smoke.
echo 'export SDL_VIDEODRIVER=dummy' >> "$CLAUDE_ENV_FILE"
