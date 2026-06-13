-- 06_looter.lua
-- Fila de corpos: quando o alvo atacado some do mapa, a posição entra na fila.
-- O macro caminha até lá, valida que existe mesmo um container no chão (corpos
-- de monstro que fugiu são descartados sozinhos) e abre; o onContainerOpen
-- puxa os itens da lista de loot para o inventário.

Loot = { queue = {} }

local lootSet = nil
local function wantedLoot(id)
    if CFG.loot.everything then return true end
    if not lootSet then
        lootSet = {}
        for _, i in ipairs(CFG.loot.items) do lootSet[i] = true end
    end
    return lootSet[id] == true
end

-- detecta morte do alvo: o targeting atualiza Bot.lastTarget a cada tick;
-- se na varredura atual o id sumiu dos spectators, vira candidato a corpo
local lastSeenId = nil
macro(200, "Detector de corpos", function()
    if not Bot.ready() or not CFG.loot.enabled then return end
    local t = Bot.lastTarget
    if not t then return end

    if lastSeenId ~= t.id then lastSeenId = t.id end

    local stillThere = false
    for _, m in ipairs(Bot.monsters(CFG.attack.range + 2)) do
        if m:getId() == t.id then
            stillThere = true
            break
        end
    end
    if not stillThere then
        -- sumiu: provável morte (a validação final é a existência do corpo)
        table.insert(Loot.queue, { pos = t.pos, at = Bot.now() })
        Bot.lastTarget = nil
    end
end)

macro(300, "Looter", function()
    if not Bot.ready() or Bot.paused or Bot.emergency then return end
    if not CFG.loot.enabled then return end
    if Bot.fighting and not CFG.loot.duringCombat then return end

    local entry = Loot.queue[1]
    if not entry then return end

    local drop = function() table.remove(Loot.queue, 1) end

    if Bot.now() - entry.at > 15000 then return drop() end
    local me = Bot.pos()
    if not entry.pos or entry.pos.z ~= me.z then return drop() end
    local d = Bot.dist(me, entry.pos)
    if d > CFG.loot.maxDistance then return drop() end
    if d > 1 then
        Bot.walkTo(entry.pos)
        return
    end

    local opened = false
    pcall(function()
        local tile = g_map.getTile(entry.pos)
        if not tile then return end
        local top = tile:getTopUseThing()
        if top and top:isContainer() then
            g_game.open(top)
            opened = true
        end
    end)
    drop()
    if not opened then return end
end)

-- corpos abertos no chão → move itens da lista para o inventário, escalonado
-- para respeitar o intervalo mínimo de movimentação do servidor
local function handleContainer(container)
    local onMap = false
    pcall(function()
        local cItem = container:getContainerItem()
        if cItem then
            local cp = cItem:getPosition()
            onMap = cp ~= nil and cp.x ~= 65535
        end
    end)
    if not onMap then return end  -- é mochila/inventário, não corpo

    local delay = 150
    for _, item in ipairs(container:getItems()) do
        if wantedLoot(item:getId()) then
            local count = math.max(item:getCount(), 1)
            Bot.schedule(delay, function()
                local dest = Bot.freeSlotPos()
                if dest then
                    pcall(function() g_game.move(item, dest, count) end)
                end
            end)
            delay = delay + 350
        end
    end
    Bot.schedule(delay + 250, function()
        pcall(function() g_game.close(container) end)
    end)
end

if type(onContainerOpen) == "function" then
    onContainerOpen(function(container, previousContainer)
        if CFG.loot.enabled then
            pcall(handleContainer, container)
        end
    end)
end
