#!/usr/bin/env python3
"""Entry point do harness de QA por visão de tela.

Uso:
    python run.py            # abre o painel de controle
    python run.py calibrate  # só roda a calibração das regiões da tela

Rode na MÁQUINA onde o cliente do seu servidor está aberto. Requer as
dependências de runtime (ver requirements.txt).
"""

import sys

from vision_bot.panel import Panel


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "calibrate":
        from vision_bot.calibrate import run_calibration
        run_calibration()
        return
    Panel().run()


if __name__ == "__main__":
    main()
