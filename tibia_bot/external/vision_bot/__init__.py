# vision_bot — harness de QA por visão de tela para OTServ próprio.
#
# Bot EXTERNO: captura a janela do cliente, lê o estado pela própria interface
# (barras de HP/mana, battle list, log) e age por teclado/mouse. Não lê memória
# nem depende de arquivos do cliente. Pensado para QA do SEU servidor: medir a
# curva de XP, estimar tempo até um level alvo, avaliar desempenho e sinalizar
# anomalias/bugs para revisão humana.
#
# As dependências pesadas (mss, opencv, pytesseract, pydirectinput) são
# importadas de forma preguiçosa dentro de cada módulo de runtime, então os
# módulos de lógica pura (state, qa) podem ser importados e testados só com
# Pillow + stdlib.

__version__ = "0.1.0"
