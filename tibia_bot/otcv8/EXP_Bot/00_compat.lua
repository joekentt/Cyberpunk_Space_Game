-- 00_compat.lua
-- Camada de compatibilidade: isola o resto do bot das variações de API entre
-- builds do OTCv8. Todo acesso ao cliente passa por `Bot.*`. Se algo mudar de
-- nome numa versão futura do OTCv8, este é o ÚNICO arquivo a ajustar.

Bot = Bot or {}

Bot.paused = false      -- pausa manual (botão no painel): trava cavebot/target/loot
Bot.emergency = false   -- pausa automática por HP crítico: trava cavebot/loot
Bot.fighting = false    -- targeting marca quando há alvo engajado
Bot.lastTarget = nil    -- {id, pos, name, hp} do último alvo atacado

function Bot.lp()
    return g_game.getLocalPlayer()
end

function Bot.ready()
    return g_game.isOnline() and Bot.lp() ~= nil
end

function Bot.now()
    return g_clock.millis()
end

-- agenda um callback em `ms` milissegundos (usa o schedule do bot se existir)
function Bot.schedule(ms, fn)
    if type(schedule) == "function" then
        schedule(ms, fn)
    else
        scheduleEvent(fn, ms)
    end
end

-- ---------- estado do jogador ----------

function Bot.hpPercent()
    if type(hppercent) == "function" then return hppercent() end
    return Bot.lp():getHealthPercent()
end

function Bot.manaPercent()
    if type(manapercent) == "function" then return manapercent() end
    local p = Bot.lp()
    local maxm = p:getMaxMana()
    if not maxm or maxm <= 0 then return 100 end
    return math.floor(p:getMana() * 100 / maxm)
end

function Bot.mana()
    return Bot.lp():getMana() or 0
end

function Bot.level()
    return Bot.lp():getLevel() or 0
end

function Bot.pos()
    return Bot.lp():getPosition()
end

function Bot.freeCap()
    local ok, cap = pcall(function() return Bot.lp():getFreeCapacity() end)
    if ok and cap then return cap end
    return 9999
end

-- escreve no console do bot (info/warn/print, o que existir nesta build)
function Bot.log(msg)
    if type(info) == "function" then info(msg)
    elseif type(warn) == "function" then warn(msg)
    elseif type(print) == "function" then print(msg) end
end

-- ---------- ações ----------

function Bot.say(text)
    if type(say) == "function" then
        say(text)
    else
        g_game.talk(text)
    end
end

-- usa item por id, estilo hotkey (procura no inventário/containers abertos)
function Bot.useItem(id)
    pcall(function() g_game.useInventoryItem(id) end)
end

-- usa item por id em um alvo (criatura ou posição); ex.: poção em si mesmo
function Bot.useItemOn(id, target)
    pcall(function() g_game.useInventoryItemWith(id, target) end)
end

-- caminha até uma posição usando o pathfinding do cliente (mapa conhecido)
function Bot.walkTo(p)
    if type(autoWalk) == "function" then
        local ok = pcall(autoWalk, p)
        if ok then return end
    end
    pcall(function() Bot.lp():autoWalk(p) end)
end

-- um passo na direção dada (0=N 1=E 2=S 3=W 4=NE 5=SE 6=SW 7=NW)
function Bot.step(dir)
    pcall(function() g_game.walk(dir) end)
end

function Bot.setChase(on)
    pcall(function() g_game.setChaseMode(on and 1 or 0) end)
end

-- ---------- mundo ----------

-- distância de Chebyshev (em sqm) entre duas posições do MESMO andar
function Bot.dist(a, b)
    return math.max(math.abs(a.x - b.x), math.abs(a.y - b.y))
end

-- monstros vivos no mesmo andar dentro de `range` sqm
function Bot.monsters(range)
    local out = {}
    if not Bot.ready() then return out end
    local me = Bot.pos()
    local ok, specs = pcall(function() return g_map.getSpectators(me, false) end)
    if not ok or not specs then return out end
    for _, c in ipairs(specs) do
        if c:isMonster() and (c:getHealthPercent() or 0) > 0 then
            local cp = c:getPosition()
            if cp and cp.z == me.z and Bot.dist(me, cp) <= range then
                table.insert(out, c)
            end
        end
    end
    return out
end

function Bot.tileWalkable(p)
    local ok, walkable = pcall(function()
        local tile = g_map.getTile(p)
        return tile and tile:isWalkable()
    end)
    return ok and walkable
end

-- conta um item por id em containers abertos + slots de equipamento
function Bot.countItem(id)
    if type(itemAmount) == "function" then
        local ok, n = pcall(itemAmount, id)
        if ok and n then return n end
    end
    local total = 0
    local ok, containers = pcall(function() return g_game.getContainers() end)
    if ok and containers then
        for _, container in pairs(containers) do
            for _, item in ipairs(container:getItems()) do
                if item:getId() == id then
                    total = total + math.max(item:getCount(), 1)
                end
            end
        end
    end
    for slot = 1, 10 do
        local oki, it = pcall(function() return Bot.lp():getInventoryItem(slot) end)
        if oki and it and it:getId() == id then
            total = total + math.max(it:getCount(), 1)
        end
    end
    return total
end

-- snapshot para o inspetor: vocação + ids de itens equipados/em containers.
-- Serve para o jogador descobrir os IDs reais do SEU servidor (RubinOT-like)
-- e preencher 01_config.lua sem adivinhação.
function Bot.inspect()
    local out = { slots = {}, containers = {} }
    if not Bot.ready() then return out end
    local ok, voc = pcall(function() return Bot.lp():getVocation() end)
    out.voc = (ok and voc) or "?"
    out.level = Bot.level()
    out.mana = Bot.mana()
    for slot = 1, 10 do
        local oki, it = pcall(function() return Bot.lp():getInventoryItem(slot) end)
        if oki and it then out.slots[slot] = it:getId() end
    end
    local okc, containers = pcall(function() return g_game.getContainers() end)
    if okc and containers then
        for _, c in pairs(containers) do
            for _, item in ipairs(c:getItems()) do
                table.insert(out.containers, item:getId())
            end
        end
    end
    return out
end

-- primeiro slot livre num container do PRÓPRIO inventário (não corpos no chão)
function Bot.freeSlotPos()
    local ok, containers = pcall(function() return g_game.getContainers() end)
    if not ok or not containers then return nil end
    for _, container in pairs(containers) do
        local isInventory = true
        local oki, cItem = pcall(function() return container:getContainerItem() end)
        if oki and cItem then
            local cp = cItem:getPosition()
            -- x == 65535 significa "dentro do inventário"; senão está no mapa (corpo)
            if cp and cp.x ~= 65535 then isInventory = false end
        end
        if isInventory and container:getItemsCount() < container:getCapacity() then
            local okp, p = pcall(function()
                return container:getSlotPosition(container:getItemsCount())
            end)
            if okp and p then return p end
        end
    end
    return nil
end
