"""
SpriteGenerator
---------------
Gera sprites procedurais de naves espaciais 2D em estilo cyberpunk.

Princípios:
  - Determinístico: a mesma seed sempre produz o mesmo sprite.
  - Por classe: cada ship_class (Small/Medium/Large) tem uma silhueta
    distinta e reconhecível à primeira vista.
  - Por facção: a paleta vem do PaletteManager e injeta a identidade visual.
  - Modular em camadas: sombra → casco → painéis → cockpit → motores → glow.
  - Top-down rotacionável: a nave aponta para +X (direita). O engine
    aplica pygame.transform.rotate, então a silhueta é simétrica
    sobre o eixo horizontal central.
  - Output: imagem RGBA da Pillow, pronta para conversão em Surface Pygame.
"""

from PIL import Image, ImageDraw
import random
import math
from typing import Tuple, List, Dict

RGBA = Tuple[int, int, int, int]

# Cor das luzes de navegação "quentes" (strobe âmbar), usada junto da cor
# accent da facção. Dá o segundo tom emissivo pedido sem apagar a identidade.
WARM_LIGHT: RGBA = (255, 190, 110, 255)


# --------------------------------------------------------------------------
# Perfis de silhueta por classe
# --------------------------------------------------------------------------
# Cada perfil é uma lista de pontos (x, y) em coordenadas normalizadas
# centradas em (0, 0), com:
#   x =  1.0  → ponta (nariz da nave, direita)
#   x = -1.0  → traseira (motores, esquerda)
#   y =  0.0  → eixo central (eixo de simetria)
#   y >  0.0  → metade superior
# O algoritmo espelha automaticamente a metade inferior.

SHIP_PROFILES: Dict[str, Dict] = {
    # ----- Modelos específicos (use model_id para selecionar) -----

    "starter_skiff": {
        # Skiff Mk I — nave inicial padrão de todo jogador.
        # Forma de "gota" achatada: módulo central compacto sem nada
        # aerodinâmico. As "saliências" laterais são pequenos RADIADORES
        # de dissipação de calor + acoplagens de hardpoints (não asas).
        # Cockpit amplo na frente, motor único discreto na traseira.
        # Vibe: civil, confiável, produção em massa para uso espacial.
        "hull": [
            (0.78, 0.00),     # nariz arredondado
            (0.68, 0.18),
            (0.52, 0.34),
            (0.30, 0.42),
            (0.10, 0.46),     # cintura - largura máxima
            (-0.05, 0.50),    # pequena projeção do radiador (curta, modular)
            (-0.15, 0.50),
            (-0.22, 0.46),
            (-0.45, 0.40),
            (-0.62, 0.28),
            (-0.78, 0.18),    # cone traseiro
            (-0.85, 0.10),
            (-0.85, 0.00),
        ],
        "canvas_size": 64,
        "fill_ratio": 0.92,
        "cockpit": [
            (0.40, 0.0, 0.14, 0.10),       # cockpit AMPLO um pouco recuado
        ],
        "engines": [(-0.85, 0.0, 0.08)],   # motor único pequeno (discreto)
        "hardpoints": [(0.15, 0.42), (-0.10, 0.48)],
        "panel_lines": [
            ((0.62, 0.0), (-0.72, 0.0)),     # quilha central
            ((0.45, 0.20), (-0.30, 0.40)),
            ((0.05, 0.46), (0.05, -0.46)),   # mamparo frontal
            ((-0.35, 0.40), (-0.35, -0.40)), # mamparo traseiro
            # Detalhes do "radiador" curto
            ((-0.05, 0.50), (-0.15, 0.50)),
            ((-0.05, -0.50), (-0.15, -0.50)),
        ],
        "nav_lights": [
            (0.70, 0.07, "warm"),     # baliza de proa
            (0.12, 0.43, "accent"),   # luz de cintura (boreste)
            (-0.10, 0.47, "warm"),    # ponta do radiador
            (-0.74, 0.11, "accent"),  # luz traseira
        ],
        "accent_stripe": [
            [(0.55, 0.20), (0.10, 0.40), (-0.20, 0.42), (-0.55, 0.30)],
        ],
    },

    "wasp_combat": {
        # Wasp — interceptador espacial. Construção MODULAR ANGULAR:
        # corpo central retangular + spinal mount frontal (canhão fino
        # com base alargada) + dois pods de hardpoint laterais (cubos
        # retangulares, não asas curvas) + bateria de motores traseira.
        # Tudo com cantos vivos e linhas retas. Estética The Expanse.
        # Vibe: plataforma de armas modular soldada em estaleiro orbital.
        "hull": [
            # Spinal mount (canhão fino projetado pra frente)
            (1.00, 0.04),    # ponta
            (0.95, 0.04),
            (0.92, 0.10),    # base do canhão alarga em cantos vivos
            (0.55, 0.10),    # encontro com o corpo central

            # Corpo central retangular (linhas retas)
            (0.55, 0.22),    # canto frontal superior do corpo
            (0.40, 0.22),    # entalhe pro pod lateral
            (0.40, 0.45),    # pod lateral frontal: canto externo inferior
            (0.20, 0.50),    # pod: borda superior plana
            (0.00, 0.50),
            (-0.05, 0.45),   # canto interno do pod
            (-0.05, 0.22),   # de volta ao corpo central

            (-0.30, 0.22),   # corpo continua reto

            # Pod lateral traseiro (igual angular)
            (-0.30, 0.45),   # canto frontal do pod traseiro
            (-0.40, 0.52),   # canto externo
            (-0.55, 0.52),
            (-0.62, 0.45),   # canto interno traseiro
            (-0.62, 0.22),   # de volta ao corpo

            # Bateria de motores em "degraus" angulares
            (-0.70, 0.22),
            (-0.78, 0.20),
            (-0.85, 0.15),   # canto da bateria
            (-0.88, 0.06),
            (-0.88, 0.00),
        ],
        "canvas_size": 80,
        "fill_ratio": 0.92,
        "cockpit": [(0.30, 0.0, 0.07, 0.05)],   # cockpit pequeno no corpo central
        "engines": [
            # Bateria de motores (vários menores em vez de 2 grandes)
            (-0.88, 0.12, 0.05),
            (-0.88, 0.0, 0.06),
            (-0.88, -0.12, 0.05),
        ],
        "hardpoints": [
            (0.97, 0.04),     # boca do canhão central
            (0.10, 0.48),     # torre do pod frontal
            (-0.48, 0.50),    # torre do pod traseiro
        ],
        "panel_lines": [
            # Detalhes técnicos retos (não curvos)
            ((0.85, 0.04), (0.55, 0.10)),     # transição do canhão
            ((0.55, 0.10), (0.55, -0.10)),    # parede frontal do corpo
            ((0.40, 0.45), (0.40, -0.45)),    # parede do pod frontal
            ((-0.30, 0.45), (-0.30, -0.45)),  # parede do pod traseiro
            ((-0.62, 0.22), (-0.62, -0.22)),  # parede da bateria
            ((0.0, 0.0), (-0.65, 0.0)),       # quilha central
            # Paineis nos pods
            ((0.40, 0.48), (0.0, 0.48)),
            ((-0.30, 0.48), (-0.55, 0.48)),
        ],
        "nav_lights": [
            (0.95, 0.07, "warm"),     # base do canhão spinal
            (0.18, 0.47, "accent"),   # torre do pod frontal
            (-0.46, 0.49, "accent"),  # torre do pod traseiro
            (-0.84, 0.15, "warm"),    # baia de motores
        ],
        "accent_stripe": [
            [(0.55, 0.16), (-0.05, 0.16), (-0.30, 0.16), (-0.62, 0.16)],
        ],
    },

    "albatross_explorer": {
        # Albatross — sonda exploradora espacial. Corpo central magro
        # estruturado tipo "satélite", com PAINEIS SOLARES/RADIADORES
        # estendidos lateralmente (forma retangular, não aerodinâmica),
        # array de SENSORES frontais (nariz com prongs), motor único
        # grande na traseira. Inspirado em Voyager/New Horizons/Cassini.
        # Vibe: probe científica, instrumentos expostos, sem nada que
        # sugira aerodinâmica.
        "hull": [
            (1.00, 0.0),     # ponta do array de sensores frontal
            (0.95, 0.05),
            (0.85, 0.06),    # base do array
            (0.78, 0.16),
            (0.60, 0.16),    # corpo central começa (módulo principal)
            (0.55, 0.40),    # painel solar frontal - retangular, não asa!
            (0.50, 0.48),    # canto externo do painel
            (0.20, 0.50),    # painel é retangular (lado externo plano)
            (0.15, 0.42),
            (0.10, 0.20),    # volta ao corpo central
            (-0.10, 0.20),
            (-0.15, 0.42),
            (-0.20, 0.50),   # segundo painel solar (traseiro)
            (-0.55, 0.50),
            (-0.60, 0.42),
            (-0.65, 0.20),   # volta ao corpo (atrás dos painéis)
            (-0.75, 0.18),
            (-0.85, 0.14),   # cone do motor
            (-0.90, 0.08),
            (-0.90, 0.0),
        ],
        "canvas_size": 80,
        "fill_ratio": 0.94,
        "cockpit": [(0.35, 0.0, 0.08, 0.06)],
        "engines": [(-0.90, 0.0, 0.10)],       # motor único grande
        "hardpoints": [
            (0.95, 0.0),                          # array de sensor frontal
            (0.35, 0.48),                         # antena no painel 1
            (-0.40, 0.48),                        # antena no painel 2
        ],
        "panel_lines": [
            ((0.85, 0.0), (-0.75, 0.0)),          # quilha do módulo central
            # Linhas dos painéis solares (formam padrão de células)
            ((0.50, 0.20), (0.50, 0.48)),         # divisória vertical painel 1
            ((0.30, 0.20), (0.30, 0.48)),         # célula do painel 1
            ((0.20, 0.20), (0.20, 0.48)),
            ((-0.25, 0.20), (-0.25, 0.50)),       # painel 2
            ((-0.40, 0.20), (-0.40, 0.50)),
            ((-0.55, 0.20), (-0.55, 0.50)),
            # Linha frontal do array de sensores
            ((0.78, 0.16), (0.78, -0.16)),
        ],
        "nav_lights": [
            (0.95, 0.05, "warm"),     # ponta do array de sensores
            (0.35, 0.46, "accent"),   # antena do painel 1
            (-0.40, 0.46, "accent"),  # antena do painel 2
            (-0.85, 0.10, "warm"),    # motor único
        ],
        "accent_stripe": [
            [(0.78, 0.10), (0.10, 0.13), (-0.65, 0.13)],
        ],
    },

    "mule_trader": {
        # Mule — cargueiro pequeno. Forma de "caixote com nariz", priorizando
        # volume interno sobre estética. Cockpit pequeno deslocado pra frente,
        # corpo retangular dominante, dois motores grandes atrás.
        # Sem asas dignas de nota. Defesa boa, velocidade baixa.
        # Vibe: van espacial, contêiner motorizado, "trabalhador".
        "hull": [
            (0.75, 0.00),    # nariz curto
            (0.70, 0.18),
            (0.62, 0.30),
            (0.55, 0.40),    # parede do "caixote" começa
            (0.50, 0.48),
            (0.20, 0.50),    # topo do caixote (quase plano)
            (-0.20, 0.50),
            (-0.45, 0.48),
            (-0.62, 0.42),
            (-0.72, 0.30),   # parede traseira do caixote
            (-0.82, 0.22),
            (-0.88, 0.10),
            (-0.88, 0.00),
        ],
        "canvas_size": 80,
        "fill_ratio": 0.92,
        "cockpit": [(0.60, 0.0, 0.08, 0.06)],
        "engines": [
            (-0.88, 0.15, 0.10),
            (-0.88, -0.15, 0.10),
        ],
        "hardpoints": [
            (-0.15, 0.48),    # hardpoint defensivo dorsal
            (-0.50, 0.45),    # hardpoint defensivo traseiro
        ],
        "panel_lines": [
            ((0.70, 0.20), (-0.65, 0.40)),       # linha superior do caixote
            ((0.55, 0.45), (-0.55, 0.45)),       # topo do contêiner
            ((0.20, 0.50), (0.20, -0.50)),       # divisão do contêiner
            ((-0.20, 0.50), (-0.20, -0.50)),
            ((0.65, 0.0), (-0.75, 0.0)),         # quilha
        ],
        "nav_lights": [
            (0.70, 0.10, "warm"),     # proa
            (0.20, 0.47, "accent"),   # topo do contêiner (frente)
            (-0.20, 0.47, "accent"),  # topo do contêiner (traseira)
            (-0.80, 0.13, "warm"),    # baia de motores
        ],
        "accent_stripe": [
            [(0.50, 0.45), (0.20, 0.47), (-0.20, 0.47), (-0.55, 0.43)],
        ],
    },

    # ----- Perfis fallback por categoria de tamanho -----
    # Usados quando model_id não corresponde a nenhum perfil específico.

    "Small": {
        # Caça compacto — corpo curto e largo, asas dominantes em delta,
        # motor pequeno na traseira. Silhueta tipo X-Wing curto.
        "hull": [
            (0.70, 0.00),    # nariz curto e arredondado
            (0.60, 0.10),
            (0.45, 0.18),
            (0.25, 0.22),    # raiz da asa frontal
            (-0.05, 0.58),   # PICO da asa em diamante (dominante)
            (-0.35, 0.40),   # raiz traseira da asa
            (-0.50, 0.22),   # antes do motor
            (-0.65, 0.18),   # bloco motor
            (-0.70, 0.10),
            (-0.70, 0.00),
        ],
        "canvas_size": 56,
        "fill_ratio": 0.92,
        "cockpit": [(0.20, 0.0, 0.13, 0.10)],
        "engines": [(-0.70, 0.0, 0.13)],
        "hardpoints": [(-0.05, 0.52), (-0.20, 0.45)],
        "panel_lines": [
            ((0.50, 0.10), (0.10, 0.22)),
            ((0.10, 0.22), (-0.05, 0.52)),    # nervura da asa
            ((-0.30, 0.36), (-0.50, 0.20)),
        ],
        "nav_lights": [
            (0.60, 0.06, "warm"),
            (-0.05, 0.52, "accent"),   # ponta da asa em diamante
            (-0.55, 0.13, "warm"),
        ],
        "accent_stripe": [
            [(0.45, 0.12), (0.10, 0.20), (-0.05, 0.50)],
        ],
    },

    "Medium": {
        # Frigata multipropósito — pescoço curto, fuselagem central larga,
        # par de motores separados, asas curtas e robustas. Cockpit elevado.
        "hull": [
            (1.00, 0.00),    # nariz
            (0.85, 0.08),    # logo após o nariz
            (0.70, 0.10),    # "pescoço" estreito
            (0.55, 0.12),
            (0.40, 0.22),    # alarga para fuselagem central
            (0.20, 0.38),    # ponta da asa frontal
            (0.00, 0.42),
            (-0.25, 0.45),   # cantil da asa traseira (mais largo atrás)
            (-0.50, 0.42),
            (-0.65, 0.30),
            (-0.80, 0.22),   # entre os motores
            (-0.85, 0.10),
            (-0.85, 0.00),
        ],
        "canvas_size": 72,
        "fill_ratio": 0.90,
        "cockpit": [
            (0.62, 0.0, 0.10, 0.10),       # cockpit principal
            (0.40, 0.0, 0.08, 0.06),       # janela secundária atrás do cockpit
        ],
        "engines": [(-0.85, 0.20, 0.09), (-0.85, -0.20, 0.09)],
        "hardpoints": [(0.30, 0.30), (-0.10, 0.42), (-0.45, 0.38)],
        "panel_lines": [
            ((0.75, 0.05), (-0.65, 0.20)),   # linha lateral longa
            ((0.40, 0.20), (-0.25, 0.42)),   # diagonal da asa
            ((0.0, 0.0),  (-0.70, 0.0)),     # quilha central
            ((-0.25, 0.42), (-0.25, -0.42)), # mamparo transversal
        ],
        "nav_lights": [
            (0.95, 0.05, "warm"),
            (0.20, 0.36, "accent"),
            (-0.45, 0.40, "accent"),
            (-0.80, 0.11, "warm"),
        ],
        "accent_stripe": [
            [(0.70, 0.08), (0.0, 0.0), (-0.65, 0.0)],
        ],
    },

    "Large": {
        # Cargueiro/cruzador — silhueta blocosa com "degraus" retangulares,
        # ponte de comando saliente na frente, blocos modulares de carga,
        # bateria de motores na traseira. Parece um navio industrial, não oval.
        "hull": [
            (1.00, 0.00),    # ponta da ponte
            (0.95, 0.08),
            (0.88, 0.12),    # canto da ponte
            (0.82, 0.12),    # recuo: a ponte é mais estreita que o corpo
            (0.78, 0.28),    # parede da ponte → corpo
            (0.70, 0.32),    # corpo de carga começa (canto)
            (0.70, 0.50),    # bloco modular 1 (alto e retangular)
            (0.25, 0.50),    # topo retangular do bloco 1
            (0.20, 0.45),    # entalhe entre blocos
            (-0.15, 0.45),
            (-0.20, 0.50),
            (-0.55, 0.50),   # bloco modular 2
            (-0.62, 0.45),
            (-0.70, 0.40),
            (-0.80, 0.32),   # parede da bateria de motores
            (-0.92, 0.30),
            (-0.96, 0.18),
            (-1.00, 0.10),
            (-1.00, 0.00),
        ],
        "canvas_size": 112,
        "fill_ratio": 0.94,
        "cockpit": [
            (0.92, 0.0, 0.05, 0.06),       # janela da ponte
            (0.84, 0.08, 0.03, 0.04),      # janelas laterais
            (0.84, -0.08, 0.03, 0.04),
        ],
        "engines": [
            (-1.00, 0.22, 0.07),
            (-1.00, 0.07, 0.07),
            (-1.00, -0.07, 0.07),
            (-1.00, -0.22, 0.07),
        ],
        "hardpoints": [
            (0.55, 0.48), (0.05, 0.48),
            (-0.40, 0.48), (-0.70, 0.42),
        ],
        "panel_lines": [
            ((0.70, 0.45), (-0.55, 0.45)),   # linha superior dos blocos
            ((0.80, 0.0),  (-0.85, 0.0)),    # quilha
            ((0.55, 0.50), (0.55, -0.50)),   # mamparo 1 (entre blocos)
            ((0.20, 0.45), (0.20, -0.45)),   # mamparo 2
            ((-0.20, 0.50), (-0.20, -0.50)), # mamparo 3
            ((-0.55, 0.50), (-0.55, -0.50)), # mamparo 4
            ((-0.85, 0.30), (-0.85, -0.30)), # parede da bateria de motores
        ],
        "nav_lights": [
            (0.92, 0.06, "warm"),     # ponte de comando
            (0.55, 0.48, "accent"),   # bloco de carga 1
            (-0.20, 0.48, "accent"),  # bloco de carga 2
            (-0.55, 0.48, "accent"),
            (-0.92, 0.13, "warm"),    # bateria de motores
        ],
        "accent_stripe": [
            [(0.70, 0.46), (0.20, 0.46), (-0.20, 0.46), (-0.55, 0.46)],
        ],
    },
}


# --------------------------------------------------------------------------
# Utilidades de transformação de coordenadas
# --------------------------------------------------------------------------
def _profile_to_pixels(points: List[Tuple[float, float]],
                       size: int,
                       fill_ratio: float) -> List[Tuple[int, int]]:
    """
    Converte pontos normalizados (-1..1) em pixels do canvas (0..size).
    `fill_ratio` controla quanto da caixa-delimitadora a nave ocupa.
    """
    center = size / 2
    scale = (size / 2) * fill_ratio
    return [(int(center + x * scale), int(center - y * scale)) for x, y in points]


def _mirror_profile(upper_half: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Constrói o contorno completo da nave espelhando o hemisfério superior
    para baixo. Retorna um polígono fechado com ordem correta.
    """
    full = list(upper_half)
    # Hemisfério inferior: percorrer do fim ao início, invertendo o sinal de y.
    # Pular os pontos com y == 0 para não duplicar (ponta e traseira).
    for x, y in reversed(upper_half):
        if y > 0.001:
            full.append((x, -y))
    return full


def _darken(color: RGBA, amount: float) -> RGBA:
    """Escurece uma cor RGBA por uma fração (0..1)."""
    r, g, b, a = color
    f = max(0.0, 1.0 - amount)
    return (int(r * f), int(g * f), int(b * f), a)


def _lighten(color: RGBA, amount: float) -> RGBA:
    """Clareia uma cor RGBA misturando com branco."""
    r, g, b, a = color
    return (
        int(r + (255 - r) * amount),
        int(g + (255 - g) * amount),
        int(b + (255 - b) * amount),
        a,
    )


# --------------------------------------------------------------------------
# Gerador principal
# --------------------------------------------------------------------------
class SpriteGenerator:
    """
    Gera sprites de naves a partir de um perfil + paleta.
    Use `generate_ship_sprite(ship_class, palette, seed)` para o sprite final.
    """

    # --- API pública ----------------------------------------------------

    @staticmethod
    def generate_ship_sprite(ship_class: str,
                             palette: Dict[str, RGBA],
                             seed: int = 0,
                             model_id: str = None) -> Image.Image:
        """
        Gera o sprite completo de uma nave.

        A seleção de perfil segue prioridade:
          1. Se `model_id` corresponde a uma entrada em SHIP_PROFILES, usa ela.
          2. Caso contrário, usa o perfil da `ship_class` (Small/Medium/Large).
          3. Se nada bater, cai para "Small".

        A nave aponta para +X (direita). Retorna Image RGBA da Pillow.
        """
        profile = None
        if model_id and model_id in SHIP_PROFILES:
            profile = SHIP_PROFILES[model_id]
        if profile is None:
            profile = SHIP_PROFILES.get(ship_class, SHIP_PROFILES["Small"])

        size = profile["canvas_size"]
        rng = random.Random(seed)

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img, "RGBA")

        # Variações controladas por seed
        wobble = SpriteGenerator._wobble_profile(profile["hull"], rng, amount=0.04)
        full_outline = _mirror_profile(wobble)
        outline_px = _profile_to_pixels(full_outline, size, profile["fill_ratio"])

        # Inner hull (versão reduzida, para o "highlight" superior)
        inner_outline = SpriteGenerator._scale_profile(wobble, 0.78)
        inner_full = _mirror_profile(inner_outline)
        inner_px = _profile_to_pixels(inner_full, size, profile["fill_ratio"])

        # ---- Camada 1: sombra projetada (offset diagonal, leve elevação) ----
        shadow_px = [(x + 1, y + 2) for x, y in outline_px]
        draw.polygon(shadow_px, fill=(0, 0, 0, 80))

        # ---- Camada 2: casco escuro (base) — deslocado pra baixo/direita,
        #      formando uma borda inferior mais escura (volume) ----
        base_px = [(x + 1, y + 2) for x, y in outline_px]
        draw.polygon(base_px, fill=palette["primary_dark"])

        # ---- Camada 3: casco principal (deslocado pra cima = pseudo-3D) ----
        hull_px = [(x, y - 1) for x, y in outline_px]
        draw.polygon(hull_px, fill=palette["primary"])

        # ---- Camada 4: highlight superior (faixa clara na parte de cima) ----
        # Pega só a metade superior do polígono e preenche com cor clara.
        draw.polygon(inner_px, fill=palette["primary_light"])
        # Mas só queremos o highlight em CIMA — sobrescrevemos a metade
        # inferior com a cor primary de volta:
        SpriteGenerator._fill_lower_half(draw, inner_px, palette["primary"], size)

        # ---- Camada 4b: sheen superior mais marcado (núcleo claro no topo) ----
        sheen_outline = SpriteGenerator._scale_profile(wobble, 0.50)
        sheen_full = _mirror_profile(sheen_outline)
        sheen_px = [(x, y - 1) for x, y in
                    _profile_to_pixels(sheen_full, size, profile["fill_ratio"])]
        draw.polygon(sheen_px, fill=_lighten(palette["primary_light"], 0.20))
        SpriteGenerator._fill_lower_half(draw, sheen_px, palette["primary"], size)

        # ---- Camada 5: linhas de painel (com bisel claro para profundidade) ----
        hl = _lighten(palette["primary"], 0.30)
        SpriteGenerator._draw_panel_lines(
            draw, profile["panel_lines"], size, profile["fill_ratio"],
            palette["primary_dark"], (hl[0], hl[1], hl[2], 90), rng
        )

        # ---- Camada 5b: faixa emissiva fina ("tron line") ----
        SpriteGenerator._draw_accent_stripe(
            draw, profile.get("accent_stripe", []), size,
            profile["fill_ratio"], palette["accent"]
        )

        # ---- Camada 6: hardpoints (pontos escuros nas asas) ----
        SpriteGenerator._draw_hardpoints(
            draw, profile["hardpoints"], size, profile["fill_ratio"],
            palette["primary_dark"], palette["secondary"]
        )

        # ---- Camada 7: cockpit (accent neon emissivo) ----
        SpriteGenerator._draw_cockpit(
            draw, profile["cockpit"], size, profile["fill_ratio"],
            palette["accent"], palette["glow"]
        )

        # ---- Camada 8: motores (bocal + glow forte na traseira) ----
        SpriteGenerator._draw_engines(
            draw, profile["engines"], size, profile["fill_ratio"],
            palette["accent"], palette["glow"], palette["primary_dark"]
        )

        # ---- Camada 9: borda escura nítida (contorno final) ----
        SpriteGenerator._draw_outline(draw, outline_px, _darken(palette["primary_dark"], 0.3))

        # ---- Camada 10: luzes de navegação (pontos emissivos no casco) ----
        SpriteGenerator._draw_nav_lights(
            draw, profile.get("nav_lights", []), size,
            profile["fill_ratio"], palette["accent"], WARM_LIGHT
        )

        return img

    # --- helpers de geometria ------------------------------------------

    @staticmethod
    def _wobble_profile(points: List[Tuple[float, float]],
                        rng: random.Random,
                        amount: float = 0.04) -> List[Tuple[float, float]]:
        """
        Aplica perturbação determinística (por seed) aos pontos internos
        da silhueta, mantendo nariz e traseira fixos para preservar a forma.
        """
        wobbled = []
        for i, (x, y) in enumerate(points):
            is_endpoint = (i == 0 or i == len(points) - 1) or abs(y) < 0.001
            if is_endpoint:
                wobbled.append((x, y))
            else:
                dx = rng.uniform(-amount, amount)
                dy = rng.uniform(-amount, amount)
                wobbled.append((x + dx, y + dy))
        return wobbled

    @staticmethod
    def _scale_profile(points: List[Tuple[float, float]],
                       factor: float) -> List[Tuple[float, float]]:
        """Escala um perfil em torno da origem, mantendo proporções."""
        return [(x * factor, y * factor) for x, y in points]

    @staticmethod
    def _fill_lower_half(draw: ImageDraw.ImageDraw,
                         polygon_px: List[Tuple[int, int]],
                         color: RGBA,
                         size: int):
        """
        Sobrescreve a metade INFERIOR do polígono (y > size/2) com `color`,
        para que o highlight claro fique só na metade superior.
        Faz isso criando uma máscara: parte do polígono que está abaixo
        do eixo central horizontal.
        """
        # Clipar o polígono à metade inferior é complexo; vamos usar
        # uma abordagem prática: desenhar um retângulo cobrindo a metade
        # inferior e fazer interseção via máscara.
        mask = Image.new("L", draw.im.size if hasattr(draw, "im") else (size, size), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.polygon(polygon_px, fill=255)
        mdraw.rectangle([0, 0, size, size // 2], fill=0)  # zera o topo
        # Aplicar a cor onde a máscara é 255
        overlay = Image.new("RGBA", (size, size), color)
        # truque: pintar usando o método de bitmap (mais simples: paste)
        # como `draw` aponta para uma Image específica, precisamos colar nela.
        base_img = draw._image if hasattr(draw, "_image") else None
        if base_img is None:
            # Pillow recente: ImageDraw guarda a imagem em `._image`
            base_img = draw.im
            # fallback: usar fill direto via polygon "lower half"
            # gera polígono recortado simples (linhas y>=size/2)
            lower_pts = [(x, max(y, size // 2)) for (x, y) in polygon_px
                         if y >= size // 2 - 1]
            if len(lower_pts) >= 3:
                draw.polygon(lower_pts, fill=color)
            return
        try:
            base_img.paste(overlay, (0, 0), mask)
        except Exception:
            pass

    @staticmethod
    def _draw_outline(draw: ImageDraw.ImageDraw,
                      polygon_px: List[Tuple[int, int]],
                      color: RGBA):
        """Desenha o contorno escuro nítido do casco."""
        # Linha fechada
        pts = polygon_px + [polygon_px[0]]
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=color, width=1)

    @staticmethod
    def _draw_panel_lines(draw: ImageDraw.ImageDraw,
                          lines_norm: List[Tuple[Tuple[float, float], Tuple[float, float]]],
                          size: int,
                          fill_ratio: float,
                          color: RGBA,
                          hi_color: RGBA,
                          rng: random.Random):
        """
        Desenha linhas de painel no casco (ambos hemisférios). Cada linha leva
        um bisel: o sulco escuro (`color`) e, 1px abaixo, um realce claro
        translúcido (`hi_color`) — dá a leitura de "chapa montada" com volume.
        """
        def _seg(pa, pb):
            # Realce claro 1px abaixo (parece luz batendo na quina da chapa)
            draw.line([(pa[0], pa[1] + 1), (pb[0], pb[1] + 1)], fill=hi_color, width=1)
            # Sulco escuro por cima
            draw.line([pa, pb], fill=color, width=1)

        for (a, b) in lines_norm:
            pa = _profile_to_pixels([a], size, fill_ratio)[0]
            pb = _profile_to_pixels([b], size, fill_ratio)[0]
            _seg(pa, pb)
            # Espelhar para o hemisfério oposto
            if abs(a[1]) > 0.001 or abs(b[1]) > 0.001:
                pa2 = _profile_to_pixels([(a[0], -a[1])], size, fill_ratio)[0]
                pb2 = _profile_to_pixels([(b[0], -b[1])], size, fill_ratio)[0]
                _seg(pa2, pb2)

    @staticmethod
    def _draw_hardpoints(draw: ImageDraw.ImageDraw,
                         hps: List[Tuple[float, float]],
                         size: int,
                         fill_ratio: float,
                         dark: RGBA,
                         mid: RGBA):
        """Desenha hardpoints (montagens de armas) como pequenos blocos."""
        for (nx, ny) in hps:
            # Hemisfério superior
            x, y = _profile_to_pixels([(nx, ny)], size, fill_ratio)[0]
            draw.rectangle([x - 1, y - 1, x + 1, y + 1], fill=dark)
            draw.point((x, y), fill=mid)
            # Espelhar
            if abs(ny) > 0.001:
                x2, y2 = _profile_to_pixels([(nx, -ny)], size, fill_ratio)[0]
                draw.rectangle([x2 - 1, y2 - 1, x2 + 1, y2 + 1], fill=dark)
                draw.point((x2, y2), fill=mid)

    @staticmethod
    def _draw_cockpit(draw: ImageDraw.ImageDraw,
                      cockpits: List[Tuple[float, float, float, float]],
                      size: int,
                      fill_ratio: float,
                      accent: RGBA,
                      glow: RGBA):
        """Desenha um ou mais cockpits/janelas emissivas."""
        center = size / 2
        scale = (size / 2) * fill_ratio
        for (cx, cy, rx, ry) in cockpits:
            px = center + cx * scale
            py = center - cy * scale
            rxp = max(1, rx * scale)
            ryp = max(1, ry * scale)
            # Halo
            draw.ellipse(
                [px - rxp - 1, py - ryp - 1, px + rxp + 1, py + ryp + 1],
                fill=glow,
            )
            # Núcleo acesso
            draw.ellipse(
                [px - rxp, py - ryp, px + rxp, py + ryp],
                fill=accent,
            )
            # Highlight branco no centro
            draw.point((int(px), int(py)), fill=_lighten(accent, 0.6))

    @staticmethod
    def _draw_engines(draw: ImageDraw.ImageDraw,
                      engines: List[Tuple[float, float, float]],
                      size: int,
                      fill_ratio: float,
                      accent: RGBA,
                      glow: RGBA,
                      primary_dark: RGBA):
        """
        Desenha cada motor com PRESENÇA: um bocal (housing escuro em trapézio,
        abrindo para a traseira -X) e um glow em camadas com núcleo quente
        quase branco e halo na cor accent.

        A nave aponta para +X, então a traseira/escape fica em -X (esquerda).
        O glow é puxado levemente para fora (-X) para sentar na borda traseira
        real do casco, e seu raio é limitado para nunca cortar no canvas.
        """
        center = size / 2
        scale = (size / 2) * fill_ratio
        nozzle_dark = _darken(primary_dark, 0.35)

        for (ex, ey, er) in engines:
            px = center + ex * scale
            py = center - ey * scale
            # Motor maior e mais presente que antes (~+40%).
            rp = max(2.0, er * scale * 1.4)

            # ---- Bocal (housing): trapézio escuro apoiado no casco, abrindo
            #      para a traseira. Fica dentro do casco (não corta). ----
            depth = rp * 1.4          # quanto o bocal entra no corpo (+X)
            outer_h = rp * 1.15       # meia-altura na boca (traseira)
            inner_h = rp * 0.62       # meia-altura no fundo (dentro do corpo)
            nozzle = [
                (px, py - outer_h),               # boca superior (na borda)
                (px + depth, py - inner_h),        # fundo superior (no corpo)
                (px + depth, py + inner_h),        # fundo inferior
                (px, py + outer_h),               # boca inferior
            ]
            draw.polygon(nozzle, fill=nozzle_dark)

            # ---- Glow centrado na borda traseira; raio ESTRITAMENTE limitado
            #      ao canvas (a faixa faint nunca toca o limite). ----
            gx = px
            edge_room = min(gx, py, size - gx, size - py) - 1.0
            r_out = max(1.5, min(rp * 1.9, edge_room))
            k = r_out / (rp * 1.9)    # fator de compressão se faltar espaço
            r_core = rp * k
            r_hot = r_core * 0.55

            ga = glow[:3]
            # Halo externo (suave)
            draw.ellipse([gx - r_out, py - r_out, gx + r_out, py + r_out],
                         fill=(ga[0], ga[1], ga[2], max(30, glow[3] - 40)))
            # Halo médio (mais denso)
            r_mid = r_out * 0.7
            draw.ellipse([gx - r_mid, py - r_mid, gx + r_mid, py + r_mid],
                         fill=(ga[0], ga[1], ga[2], min(255, glow[3] + 70)))
            # Núcleo na cor accent
            draw.ellipse([gx - r_core, py - r_core, gx + r_core, py + r_core],
                         fill=accent)
            # Centro quente quase branco
            draw.ellipse([gx - r_hot, py - r_hot, gx + r_hot, py + r_hot],
                         fill=_lighten(accent, 0.85))

    @staticmethod
    def _draw_accent_stripe(draw: ImageDraw.ImageDraw,
                            stripes: List[List[Tuple[float, float]]],
                            size: int,
                            fill_ratio: float,
                            accent: RGBA):
        """
        Faixa emissiva fina ("tron line") acompanhando o corpo. Desenhada com
        um glow translúcido largo + um núcleo fino claro. Espelhada para o
        hemisfério oposto quando sai do eixo central.
        """
        a = accent[:3]
        for poly in stripes:
            if len(poly) < 2:
                continue
            pts = [_profile_to_pixels([p], size, fill_ratio)[0] for p in poly]
            draw.line(pts, fill=(a[0], a[1], a[2], 70), width=3, joint="curve")
            draw.line(pts, fill=(_lighten(accent, 0.45)[:3] + (180,)), width=1)
            # Espelho
            if any(abs(y) > 0.001 for _, y in poly):
                mpts = [_profile_to_pixels([(x, -y)], size, fill_ratio)[0]
                        for x, y in poly]
                draw.line(mpts, fill=(a[0], a[1], a[2], 70), width=3, joint="curve")
                draw.line(mpts, fill=(_lighten(accent, 0.45)[:3] + (180,)), width=1)

    @staticmethod
    def _draw_nav_lights(draw: ImageDraw.ImageDraw,
                         lights: List[Tuple[float, float, str]],
                         size: int,
                         fill_ratio: float,
                         accent: RGBA,
                         warm: RGBA):
        """
        Luzes de navegação: pequenos pontos emissivos espalhados pelo casco,
        na cor accent da facção e numa cor "quente" secundária. Cada luz tem
        um micro-halo + núcleo claro. Espelhadas para os dois hemisférios.
        """
        center = size / 2
        scale = (size / 2) * fill_ratio
        for (nx, ny, kind) in lights:
            col = warm if kind == "warm" else accent
            positions = [(nx, ny)]
            if abs(ny) > 0.001:
                positions.append((nx, -ny))
            for (sx, sy) in positions:
                px = center + sx * scale
                py = center - sy * scale
                # Micro-halo
                draw.ellipse([px - 1.8, py - 1.8, px + 1.8, py + 1.8],
                             fill=(col[0], col[1], col[2], 80))
                # Núcleo
                draw.ellipse([px - 0.9, py - 0.9, px + 0.9, py + 0.9], fill=col)
                # Brilho central
                draw.point((int(round(px)), int(round(py))), fill=_lighten(col, 0.6))
