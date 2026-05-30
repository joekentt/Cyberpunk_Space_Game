# ADR 002 — Coerência espacial: naves devem parecer espaciais, não aéreas

**Data:** 2026-05-25
**Status:** Aceito

## Contexto

Durante a Fase 2 (catálogo Tier 1), os perfis iniciais de `wasp_combat` e `albatross_explorer` foram desenhados com inspiração em caças e exploradores **atmosféricos** terrestres (estilo F-22 e U-2). A revisão identificou que isso quebra a coerência do mundo do jogo: a ação se passa inteiramente no espaço, e formas aerodinâmicas não fazem sentido lá.

### O problema técnico

No vácuo:
- **Não há sustentação aerodinâmica** — asas não geram lift sem ar para empurrar
- **Não há arrasto** — formato pontudo não economiza energia
- **Manobras vêm de RCS thrusters** posicionados em vários pontos do casco, não de superfícies de controle
- **Calor é problema sério** — naves espaciais reais têm radiadores grandes e expostos
- **Hardpoints ficam expostos** — não precisam de fairings/cobertura aerodinâmica
- **Forma pode ser qualquer uma** — cubo, treliça, módulos empilhados

### O problema estético

Naves com nariz cônico, asas em delta curvas e fuselagem simétrica tipo "avião" criam dissonância com:
- Lore cyberpunk-espacial onde tudo se passa entre estações orbitais
- Estética modular que o resto do projeto adota (carga, módulos, hardpoints visíveis)
- Naves espaciais "bem pensadas" de referências do gênero (The Expanse, EVE, Babylon 5)

## Decisão

Todos os perfis de naves em `SHIP_PROFILES` devem seguir os seguintes princípios de coerência espacial:

### 1. Geometria modular sobre curvas aerodinâmicas
- **Preferir:** linhas retas, cantos vivos, formas retangulares, perfis "soldados"
- **Evitar:** curvas suaves contínuas, perfis em "gota aerodinâmica", deltas afilados

### 2. Saliências têm função explícita
Qualquer estrutura projetada lateralmente do corpo deve representar funcionalidade visível, não "asa":
- **Pods de hardpoint** (formato retangular, terminam em torre/canhão)
- **Painéis solares ou radiadores** (formato retangular com células/divisórias visíveis)
- **Arrays de antenas ou sensores** (estruturas longas e finas)
- **Tanques externos** de combustível ou propelente
- **Braços manipuladores** (mineradoras, naves de reparo)

### 3. Sistema de propulsão expressivo
- **Cluster de motores múltiplos** ou bateria traseira, em vez de "motor único aerodinâmico"
- RCS thrusters podem ser sugeridos por pequenos pontos brilhantes em vários cantos do casco (futuro)

### 4. Frente da nave
A "frente" (lado +X que aponta para a direção de movimento) não precisa ser cônica/afilada. Pode ser:
- **Spinal mount** (canhão alongado projetando-se à frente)
- **Ponte de comando saliente** (estilo cargueiro/cruzador)
- **Array de sensores** (estilo sonda)
- **Plataforma de docking** (parede plana com porta)

### 5. Simetria é opcional
Naves espaciais não precisam ser simétricas. Pode haver assimetrias: um pod só de um lado, um braço manipulador, uma antena saliente.

## Aplicação no Tier 1

Após a revisão, os perfis foram redesenhados:

| Modelo | Antes | Depois |
|---|---|---|
| `wasp_combat` | Caça em delta tipo F-22 | Plataforma modular angular com spinal mount + pods retangulares + bateria de motores |
| `albatross_explorer` | Planador tipo U-2 com asas longas | Sonda científica com painéis solares estruturados (células visíveis) + array de sensores frontal |
| `starter_skiff` | Gota com asinhas curtas | Gota com radiadores curtos modulares (pequena projeção retangular) |
| `mule_trader` | (já estava OK) | Caixote modular com bateria de motores |

## Consequências

### Positivas
- Coerência com o lore (jogo se passa só no espaço)
- Diferenciação clara entre naves do nosso jogo e estética de jogos atmosféricos
- Direção visual alinhada com referências sólidas do gênero
- Princípio claro para guiar adição de naves futuras

### Negativas
- Sprites angulares perdem um pouco da "elegância visual" de linhas curvas
- Algumas naves ficam visualmente mais "duras" — pode-se compensar com VFX e iluminação

### Mitigação
- Quando um perfil precisar parecer "elegante", investir em **estética da estrutura modular** (linhas de painel sofisticadas, cockpit emissivo, glow do motor) em vez de curvas
- Pode haver exceções (naves Marth high-tech podem ter linhas mais sofisticadas) mas a justificativa deve ser do mundo, não "fica mais bonito como avião"

## Auditoria recomendada para novas naves

Antes de adicionar um perfil em `SHIP_PROFILES`, verificar:

- [ ] Há nariz cônico afilado tipo avião? Se sim, redesenhar.
- [ ] Há asas curvas em delta? Se sim, redesenhar como pods/painéis retangulares.
- [ ] As saliências têm função visível identificável?
- [ ] Há cantos vivos / linhas retas dominantes?
- [ ] A nave parece "soldada/montada" ou "moldada como avião"?

Esses 5 pontos cobrem ~95% dos erros que produzem aparência aérea acidental.
