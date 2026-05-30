# ADR 001 — Modelos fixos de naves em vez de módulos visuais

**Data:** 2026-05-25
**Status:** Aceito

## Contexto

A Especificação Técnica de Geração Procedural original previa que módulos equipados em uma nave alterariam tanto suas **estatísticas** quanto sua **aparência visual** (via `ModuleVisualDescriptor`), com armas, motores e outros componentes sendo desenhados sobre o casco em hardpoints tipados.

Durante implementação inicial, identificamos três obstáculos práticos:

1. **Escala dos sprites.** Naves geradas têm 56-112 pixels de lado e rotacionam livremente. Detalhes de módulo em 2-5 pixels disponíveis nas asas viram borrão na rotação e não comunicam diferença para o jogador.
2. **Complexidade vs payoff.** Implementar composição modular requer `ModuleVisualDescriptor`, sub-geradores de assets por tipo de módulo, hardpoints tipados nas naves, invalidação de cache por loadout, e regras de oclusão entre camadas. Estimativa de 2-4 sessões focadas para um payoff visual marginal.
3. **Pilar de design conflitante.** A especificação de Naves/Módulos/Progressão estabelece "**No ship crafting**" como pilar. A fantasia central é "comprei/saqueei uma nave de um catálogo", não "construí esta nave". Módulos visuais empurram a estética para o pilar oposto (Cosmoteer/Avorion) em detrimento da experiência tipo Elite Dangerous que o jogo busca.

## Decisão

Adotamos o modelo do **Elite Dangerous**: naves são modelos fixos com silhueta própria. Módulos equipados afetam apenas estatísticas (dano, velocidade, energia, calor) e **VFX** (cor de tiro, intensidade de glow do motor, padrão de escudo).

A diferenciação visual entre naves vem de:

- Catálogo de modelos distintos (Skiff Mk I, futuros: caça de combate, cargueiro pequeno, exploradora, etc.)
- Paleta por facção (`PaletteManager`)
- Estado de dano progressivo (`DamageStateRenderer` — futuro)
- VFX por loadout: cor de projéteis, glow de motor, aura de escudo
- Pequenos overlays cosméticos: insígnias, decals, marcas de elite

## Consequências

### Positivas
- Velocidade de implementação muito maior — Fase 1 (este commit) entregue em uma sessão
- Cache de sprites simples e robusto (`model_id × faction × seed`)
- Caminho de migração para arte manual é trivial no futuro (substituir PNG por modelo, sem refazer composição)
- VFX dinâmicos comunicam o loadout sem custo geométrico
- Modelos têm identidade visual forte (você reconhece uma "Skiff" de longe)

### Negativas
- Customização visual do jogador é menor — você não vê os hardpoints do seu inimigo só pela silhueta
- Naves do mesmo modelo são visualmente idênticas (mitigado por paleta de facção)
- A especificação técnica original precisa ser revisada — `ModuleVisualDescriptor` está cancelado

### Mitigação
- Investir em VFX expressivos de combate (cor de tiro, aura de impacto, padrão de escudo) para compensar a falta de diferenciação por sprite
- Manter o catálogo de modelos crescendo — meta inicial: 6-8 modelos antes de considerar features mais profundas
- Reservar a opção de adicionar "skins" / "decals" cosméticos depois (rotas de venda em estações, recompensas de missão de elite)

## Implementação inicial (Fase 1)

- Campo `model_id` adicionado ao `Ship` dataclass
- `SpriteGenerator` consulta `model_id` antes de `ship_class` na escolha de perfil
- Perfil `starter_skiff` criado em `SHIP_PROFILES`
- `Skiff Mk I` adicionada ao `ships.json` como nave inicial padrão (`starting_ship: true`)
- `main_pygame.py` instancia o jogador com a Skiff

## Próximas fases

2. Catálogo de modelos adicionais (3-4 modelos do tier inicial)
3. Sistema de aquisição (mercado de naves em estações + loot raro)
4. Estatísticas dos módulos realmente derivadas (substituir valores fixos)
5. VFX por arma (cor, padrão de impacto, intensidade)
6. Modelos avançados (tiers superiores)
