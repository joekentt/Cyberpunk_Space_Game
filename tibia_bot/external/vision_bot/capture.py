"""Captura de tela do cliente. mss importado de forma preguiçosa.

O bot captura UMA região (a janela do cliente, calibrada) por iteração e o
resto do código recorta sub-regiões relativas a esse frame.
"""


class ScreenCapture:
    def __init__(self):
        self._sct = None
        self._last = None          # (signature, PIL.Image) p/ detector de freeze

    def _ensure(self):
        if self._sct is None:
            import mss              # lazy: só na máquina do usuário
            self._sct = mss.mss()
        return self._sct

    def grab(self, region=None):
        """Captura a tela (ou a região {x,y,w,h}) e devolve uma PIL.Image RGB."""
        from PIL import Image
        sct = self._ensure()
        if region is None:
            mon = sct.monitors[1]
        else:
            mon = {"left": region["x"], "top": region["y"],
                   "width": region["w"], "height": region["h"]}
        raw = sct.grab(mon)
        img = Image.frombytes("RGB", raw.size, raw.rgb)
        return img

    @staticmethod
    def signature(img, grid=16):
        """Assinatura barata do frame (downscale → bytes) para o FreezeDetector
        comparar igualdade entre frames consecutivos."""
        small = img.convert("L").resize((grid, grid))
        return small.tobytes()
