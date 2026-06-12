-- otcv8_stub.lua
-- Ambiente fake mínimo da API do OTCv8/bot para testar o EXP_Bot headless.
-- Tudo que o bot toca (g_game, g_map, g_clock, macro, schedule, storage,
-- UI, Item, say, itemAmount, onContainerOpen) é simulado aqui e registra
-- as chamadas em Stub.* para os asserts do teste.

Stub = {
    time = 0,
    macros = {},
    scheduled = {},
    said = {},
    used = {},          -- useInventoryItem(id)
    usedWith = {},      -- useInventoryItemWith(id, target)
    moved = {},         -- g_game.move
    bought = {},        -- g_game.buyItem
    opened = {},        -- g_game.open
    steps = {},         -- g_game.walk
    items = {},         -- id -> quantidade (itemAmount)
    spectators = {},
    attacking = nil,
    chase = nil,
    walkedTo = nil,
    corpseAt = nil,
    containerCb = nil,
}

-- ---------- jogador ----------

Stub.player = {
    hp = 100, mana = 300, maxmana = 300, level = 20, voc = 4,  -- 4 = knight
    expn = 10000, x = 100, y = 100, z = 7, cap = 500,
}
local P = Stub.player
function P.getHealthPercent(self) return Stub.player.hp end
function P.getMana(self) return Stub.player.mana end
function P.getMaxMana(self) return Stub.player.maxmana end
function P.getLevel(self) return Stub.player.level end
function P.getVocation(self) return Stub.player.voc end
function P.getExperience(self) return Stub.player.expn end
function P.getFreeCapacity(self) return Stub.player.cap end
function P.getPosition(self)
    return { x = Stub.player.x, y = Stub.player.y, z = Stub.player.z }
end
function P.getInventoryItem(self, slot) return nil end
function P.autoWalk(self, p) Stub.walkedTo = p end

function Stub.makeMonster(id, name, x, y, z, hp)
    return {
        getId = function(self) return id end,
        getName = function(self) return name end,
        getHealthPercent = function(self) return hp or 100 end,
        getPosition = function(self) return { x = x, y = y, z = z } end,
        isMonster = function(self) return true end,
        isPlayer = function(self) return false end,
    }
end

Stub.corpse = {
    isContainer = function(self) return true end,
}

-- ---------- containers ----------

local inventoryBp = {
    getContainerItem = function(self) return nil end,
    getItems = function(self) return {} end,
    getItemsCount = function(self) return 0 end,
    getCapacity = function(self) return 20 end,
    getSlotPosition = function(self, slot)
        return { x = 65535, y = 64, z = slot }
    end,
}
Stub.containers = { inventoryBp }

-- ---------- API global do cliente ----------

g_clock = { millis = function() return Stub.time end }

g_game = {
    isOnline = function() return true end,
    getLocalPlayer = function() return Stub.player end,
    getContainers = function() return Stub.containers end,
    attack = function(c) Stub.attacking = c end,
    getAttackingCreature = function() return Stub.attacking end,
    setChaseMode = function(mode) Stub.chase = mode end,
    walk = function(dir) table.insert(Stub.steps, dir) end,
    turn = function(dir) Stub.turned = dir end,
    talk = function(text) Stub.onSay(text) end,
    useInventoryItem = function(id) table.insert(Stub.used, id) end,
    useInventoryItemWith = function(id, target)
        table.insert(Stub.usedWith, { id = id, target = target })
    end,
    use = function(thing) Stub.usedThing = thing end,
    open = function(thing) table.insert(Stub.opened, thing) end,
    close = function(container) Stub.closed = container end,
    move = function(item, pos, count)
        table.insert(Stub.moved, { item = item, pos = pos, count = count })
    end,
    buyItem = function(item, amount, ignoreCap, withBp)
        table.insert(Stub.bought, { item = item, amount = amount })
    end,
    safeLogout = function() Stub.loggedOut = true end,
}

g_map = {
    getSpectators = function(pos, multifloor) return Stub.spectators end,
    getTile = function(pos)
        return {
            isWalkable = function(self) return true end,
            getTopUseThing = function(self)
                if Stub.corpseAt and Stub.corpseAt.x == pos.x
                        and Stub.corpseAt.y == pos.y
                        and Stub.corpseAt.z == pos.z then
                    return Stub.corpse
                end
                return nil
            end,
        }
    end,
}

Item = {
    create = function(id)
        return { id = id, getId = function(self) return id end }
    end,
}

-- ---------- API do módulo de bot ----------

storage = {}

function macro(interval, a, b)
    local cb = b or a
    local name = type(a) == "string" and a or nil
    table.insert(Stub.macros, { interval = interval, name = name, cb = cb })
end

function schedule(ms, fn)
    table.insert(Stub.scheduled, { at = Stub.time + ms, fn = fn })
end

-- registra a fala e, se for magia (ex...), simula a queda de mana de um cast
-- bem-sucedido — é assim que Bot.verifyCasts confirma o cast no modo trust
function Stub.onSay(text)
    table.insert(Stub.said, text)
    if type(text) == "string" and text:sub(1, 2) == "ex" then
        Stub.player.mana = math.max(0, Stub.player.mana - 20)
    end
end

function say(text)
    Stub.onSay(text)
end

function itemAmount(id)
    return Stub.items[id] or 0
end

function onContainerOpen(cb)
    Stub.containerCb = cb
end

function setDefaultTab(name) end

UI = {
    Label = function(text)
        return { setText = function(self, t) self.text = t end, text = text }
    end,
    Button = function(text, fn) return { text = text, fn = fn } end,
    Separator = function() return {} end,
}

-- ---------- motor do teste ----------

-- avança o relógio, roda todos os macros e os callbacks agendados vencidos
function Stub.tick(dt)
    Stub.time = Stub.time + (dt or 200)
    for _, m in ipairs(Stub.macros) do m.cb() end
    local i = 1
    while i <= #Stub.scheduled do
        local s = Stub.scheduled[i]
        if s.at <= Stub.time then
            table.remove(Stub.scheduled, i)
            s.fn()
        else
            i = i + 1
        end
    end
end

function Stub.saidContains(text)
    for _, s in ipairs(Stub.said) do
        if s == text then return true end
    end
    return false
end
