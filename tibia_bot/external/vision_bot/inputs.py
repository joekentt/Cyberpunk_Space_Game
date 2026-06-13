"""Injeção de teclado/mouse + failsafe. Backends importados preguiçosamente.

Prioriza `pydirectinput` (envia eventos via SendInput no Windows — funciona
dentro de jogos que ignoram eventos sintéticos comuns). Cai para `pyautogui`
se indisponível. Em `dry_run`, apenas registra a ação (usado em testes/ensaios).
"""


class Inputs:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self._be = None
        self.log = []              # histórico de ações em dry_run

    def _backend(self):
        if self._be is not None:
            return self._be
        try:
            import pydirectinput as be
            be.PAUSE = 0.0
            be.FAILSAFE = True     # mouse no canto superior-esquerdo aborta
        except Exception:
            import pyautogui as be
            be.FAILSAFE = True
        self._be = be
        return be

    def _do(self, action, *args):
        self.log.append((action, args))
        if self.dry_run:
            return
        be = self._backend()
        getattr(be, action)(*args)

    def press_key(self, key):
        self._do("press", key)

    def key_down(self, key):
        self._do("keyDown", key)

    def key_up(self, key):
        self._do("keyUp", key)

    def click(self, x, y, button="left"):
        self.log.append(("click", (x, y, button)))
        if self.dry_run:
            return
        be = self._backend()
        be.moveTo(x, y)
        be.click(button=button)

    def move_to(self, x, y):
        self._do("moveTo", x, y)
