"""Teste de fumaça headless do EXP_Bot (OTCv8).

Carrega o stub da API do cliente + todos os .lua do bot na ordem real e
simula uma sessão: cura, poção, targeting, magia de ataque, loot de corpo,
cavebot andando e ciclo de refill (compra no NPC).

Requer: pip install lupa
Rodar:  python tibia_bot/tests/test_smoke.py
"""

import glob
import os
import sys

try:
    from lupa import LuaRuntime
except ImportError:
    print("SKIP: instale a dependência de teste com `pip install lupa`")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = os.path.join(HERE, "..", "otcv8", "EXP_Bot")

lua = LuaRuntime()

passed = 0


def check(cond, msg):
    global passed
    if not cond:
        print(f"FALHOU: {msg}")
        sys.exit(1)
    passed += 1
    print(f"ok {passed}: {msg}")


def run(code):
    return lua.execute(code)


def evl(code):
    return lua.eval(code)


# ---- carga: stub + arquivos do bot na ordem alfabética (como no OTCv8) ----
with open(os.path.join(HERE, "otcv8_stub.lua")) as f:
    run(f.read())

bot_files = sorted(glob.glob(os.path.join(BOT_DIR, "*.lua")))
assert len(bot_files) == 9, f"esperava 9 arquivos, achei {len(bot_files)}"
for path in bot_files:
    with open(path) as f:
        lua.execute(f.read())

check(evl("#Stub.macros >= 7"), "macros registrados no carregamento")
check(evl("Bot.profile() ~= nil and Bot.profile().name == 'knight'"),
      "vocação detectada via client id (1 = knight)")

# ---- 1. healer: HP 50% → exura ico ----
run("Stub.player.hp = 50")
run("Stub.tick()")
check(evl("Stub.saidContains('exura ico')"), "healer lança exura ico com HP 50%")

# ---- 2. poção de HP: HP 40% (< 45) com great health potion na mochila ----
run("Stub.items[7591] = 10; Stub.player.hp = 40")
run("Stub.tick(1100)")
check(evl("#Stub.usedWith > 0 and Stub.usedWith[1].id == 7591"),
      "poção de HP usada em si mesmo abaixo do gatilho")

# ---- 3. targeting: monstro adjacente → ataque + chase + exori ico ----
run("Stub.player.hp = 100")
run("Stub.spectators = { Stub.makeMonster(7, 'Rotworm', 101, 100, 7) }")
run("Stub.tick()")
check(evl("Stub.attacking ~= nil and Stub.attacking:getName() == 'Rotworm'"),
      "targeting ataca o monstro mais próximo")
check(evl("Stub.chase == 1"), "knight liga o chase mode")
check(evl("Stub.saidContains('exori ico')"),
      "magia de ataque respeitando reserva de mana")

# ---- 4. loot: monstro some → corpo detectado, aberto e saqueado ----
run("Stub.spectators = {}")
run("Stub.corpseAt = { x = 101, y = 100, z = 7 }")
run("Stub.tick()")
check(evl("#Stub.opened > 0"), "corpo do alvo morto é aberto")

run("""
local corpse = {
    getContainerItem = function(self)
        return { getPosition = function(s) return { x = 101, y = 100, z = 7 } end }
    end,
    getItems = function(self)
        return { {
            getId = function(s) return 2148 end,
            getCount = function(s) return 50 end,
        } }
    end,
}
Stub.containerCb(corpse)
""")
run("Stub.tick(2000)")
check(evl("#Stub.moved > 0 and Stub.moved[1].count == 50"),
      "gold coins movidas do corpo para o inventário")

# ---- 5. cavebot: sem alvo/corpo → anda até o waypoint ----
run("Stub.corpseAt = nil")
run("storage.wp_hunt = { { type = 'walk', x = 110, y = 100, z = 7 } }")
run("Stub.tick()")
check(evl("Stub.walkedTo ~= nil and Stub.walkedTo.x == 110"),
      "cavebot caminha em direção ao waypoint de hunt")

# ---- 6. refill: sem mana potion → rota de refill + compra no NPC ----
run("storage.wp_refill = { { type = 'buy', x = 100, y = 101, z = 7 } }")
run("Stub.tick()")        # precisa de refill (strong mana 7589 = 0) → muda de modo
check(evl("Stub.saidContains('hi')"), "fala com o NPC ao chegar no waypoint de compra")
run("Stub.tick(5000)")    # roda a sequência agendada: trade + compras
check(evl("Stub.saidContains('trade')"), "abre o trade do NPC")
check(evl("#Stub.bought > 0"), "compra os supplies em falta via protocolo")

# ---- 7. emergência: HP crítico congela cavebot, healer segue ----
run("Stub.player.hp = 10; Stub.walkedTo = nil")
run("Stub.tick(1100)")
check(evl("Bot.emergency == true"), "modo emergência ativa com HP crítico")
check(evl("Stub.walkedTo == nil"), "cavebot congelado durante a emergência")
run("Stub.player.hp = 80")
run("Stub.tick(1100)")
check(evl("Bot.emergency == false"), "emergência desativa ao recuperar HP")

print(f"\ntodos os {passed} checks passaram")
