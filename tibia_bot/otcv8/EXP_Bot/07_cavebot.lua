-- 07_cavebot.lua
-- Andarilho por waypoints com dois circuitos:
--   wp_hunt   → loop fechado da área de caçada (repete para sempre)
--   wp_refill → rota até a cidade (banco/NPC) percorrida UMA vez quando os
--               supplies acabam; ao terminar, volta ao waypoint de hunt
--               mais próximo e o ciclo recomeça.
--
-- Tipos de waypoint:
--   walk    apenas caminhar até a posição
--   use     usar o item do topo da posição (corda, alavanca, escada deitada)
--   deposit falar com NPC banqueiro: hi → deposit all → yes
--   buy     falar com NPC vendedor:  hi → trade → compra os supplies em falta
--
-- As rotas são gravadas in-game pelos botões do painel (08_panel.lua) e
-- persistem no storage do config (sobrevivem a relog/restart).

storage.wp_hunt = storage.wp_hunt or {}
storage.wp_refill = storage.wp_refill or {}

Cave = {
    mode = "hunt",      -- "hunt" | "refill"
    idx = 1,
    stuckTicks = 0,
    lastPos = nil,
    busyUntil = 0,      -- janela de espera após ações de NPC
}

local function activeList()
    return Cave.mode == "refill" and storage.wp_refill or storage.wp_hunt
end

local function needsRefill()
    if Bot.freeCap() < CFG.supplies.minCap then return true end
    for _, rule in ipairs(Bot.supplyRules()) do
        if Bot.countItem(rule.id) < rule.min then return true end
    end
    return false
end

-- índice do waypoint de hunt mais próximo (para retomar após o refill)
local function nearestHuntIdx()
    local me, bestIdx, bestDist = Bot.pos(), 1, math.huge
    for i, wp in ipairs(storage.wp_hunt) do
        if wp.z == me.z then
            local d = Bot.dist(me, wp)
            if d < bestDist then bestIdx, bestDist = i, d end
        end
    end
    return bestIdx
end

local function advance()
    Cave.idx = Cave.idx + 1
    Cave.stuckTicks = 0
    local list = activeList()
    if Cave.idx > #list then
        if Cave.mode == "refill" then
            Cave.mode = "hunt"
            Cave.idx = nearestHuntIdx()
        else
            Cave.idx = 1
        end
    end
end

-- ----- ações de NPC (sequências de fala escalonadas) -----

local function doDeposit()
    Bot.say("hi")
    Bot.schedule(1200, function() Bot.say("deposit all") end)
    Bot.schedule(2400, function() Bot.say("yes") end)
    Cave.busyUntil = Bot.now() + 3500
end

local function doBuy()
    Bot.say("hi")
    Bot.schedule(1200, function() Bot.say("trade") end)
    local delay = 2600
    for _, rule in ipairs(Bot.supplyRules()) do
        local have = Bot.countItem(rule.id)
        local need = (rule.buyTo or rule.min * 4) - have
        if need > 0 then
            Bot.schedule(delay, function()
                -- compra direto pelo protocolo; o servidor valida a loja
                pcall(function()
                    g_game.buyItem(Item.create(rule.id), need, true, false)
                end)
            end)
            delay = delay + 800
        end
    end
    Cave.busyUntil = Bot.now() + delay + 1000
end

local function doUse(wp)
    pcall(function()
        local tile = g_map.getTile({ x = wp.x, y = wp.y, z = wp.z })
        local top = tile and tile:getTopUseThing()
        if top then g_game.use(top) end
    end)
    Cave.busyUntil = Bot.now() + 1500
end

-- ----- loop principal -----

macro(300, "CaveBot", function()
    if not Bot.ready() or Bot.paused or Bot.emergency then return end
    -- combate e loot têm prioridade sobre andar
    if Bot.fighting then return end
    if CFG.loot.enabled and #Loot.queue > 0 then return end
    if Bot.now() < Cave.busyUntil then return end

    if Cave.mode == "hunt" and #storage.wp_refill > 0 and needsRefill() then
        Cave.mode = "refill"
        Cave.idx = 1
        Cave.stuckTicks = 0
    end

    local list = activeList()
    if #list == 0 then return end
    if Cave.idx > #list then Cave.idx = 1 end

    local wp = list[Cave.idx]
    local me = Bot.pos()

    -- andar errado (escada/buraco mudou o z): tenta achar à frente um
    -- waypoint no andar atual; se não houver, pula o atual
    if wp.z ~= me.z then
        for ahead = 1, math.min(5, #list) do
            local j = Cave.idx + ahead
            if j > #list then j = j - #list end
            if list[j].z == me.z then
                Cave.idx = j
                Cave.stuckTicks = 0
                return
            end
        end
        advance()
        return
    end

    local d = Bot.dist(me, wp)
    local arriveAt = (wp.type == "walk") and 1 or 2

    if d <= arriveAt then
        if wp.type == "deposit" then
            doDeposit()
        elseif wp.type == "buy" then
            doBuy()
        elseif wp.type == "use" then
            doUse(wp)
        end
        advance()
        return
    end

    -- detector de "travado": mesma posição por muitos ticks → passo aleatório,
    -- e depois de insistir demais, pula o waypoint
    if Cave.lastPos and Cave.lastPos.x == me.x and Cave.lastPos.y == me.y
            and Cave.lastPos.z == me.z then
        Cave.stuckTicks = Cave.stuckTicks + 1
    else
        Cave.stuckTicks = 0
    end
    Cave.lastPos = { x = me.x, y = me.y, z = me.z }

    if Cave.stuckTicks > 30 then
        advance()
        return
    elseif Cave.stuckTicks > 12 and Cave.stuckTicks % 4 == 0 then
        Bot.step(math.random(0, 3))
        return
    end

    Bot.walkTo({ x = wp.x, y = wp.y, z = wp.z })
end)

-- helpers usados pelos botões do painel
function Cave.record(listName, wpType)
    if not Bot.ready() then return end
    local me = Bot.pos()
    table.insert(storage[listName], {
        type = wpType or "walk", x = me.x, y = me.y, z = me.z,
    })
end

function Cave.clear(listName)
    storage[listName] = {}
    Cave.idx = 1
    Cave.mode = "hunt"
end
