-- 08_panel.lua
-- Painel do bot: status ao vivo (vocação, estado, exp/h) e botões de
-- gravação das rotas. Toda a UI é envolvida em pcall: se os helpers de UI
-- não existirem nesta build do OTCv8, o bot continua funcionando sem painel.

local labels = {}

pcall(function()
    if type(setDefaultTab) == "function" then setDefaultTab("EXP") end
end)

local function addLabel(key, text)
    pcall(function()
        labels[key] = UI.Label(text)
    end)
end

local function setLabel(key, text)
    if labels[key] then
        pcall(function() labels[key]:setText(text) end)
    end
end

local function addButton(text, fn)
    pcall(function() UI.Button(text, fn) end)
end

local function addSeparator()
    pcall(function() UI.Separator() end)
end

-- ----- status -----
addLabel("voc", "Vocação: ?")
addLabel("state", "Estado: iniciando")
addLabel("exp", "Exp/h: -")
addLabel("route", "Rota: 0 hunt / 0 refill")
addSeparator()

-- ----- controle -----
addButton("⏯ Pausar / retomar bot", function()
    Bot.paused = not Bot.paused
end)
addSeparator()

-- ----- gravação de rota -----
addLabel("hint", "Grave a rota andando pelo respawn:")
addButton("➕ WP caçada (aqui)", function() Cave.record("wp_hunt", "walk") end)
addButton("➕ WP caçada: usar item (corda/escada)", function()
    Cave.record("wp_hunt", "use")
end)
addSeparator()
addButton("➕ WP refill (aqui)", function() Cave.record("wp_refill", "walk") end)
addButton("➕ WP refill: usar item", function() Cave.record("wp_refill", "use") end)
addButton("🏦 WP refill: depositar (NPC banco)", function()
    Cave.record("wp_refill", "deposit")
end)
addButton("🧪 WP refill: comprar supplies (NPC)", function()
    Cave.record("wp_refill", "buy")
end)
addSeparator()
addButton("🗑 Limpar rota de caçada", function() Cave.clear("wp_hunt") end)
addButton("🗑 Limpar rota de refill", function() Cave.clear("wp_refill") end)

-- ----- atualização do status + exp/h -----
local sessionStartExp = nil
local sessionStartAt = nil

macro(1000, function()
    if not Bot.ready() then
        setLabel("state", "Estado: offline")
        return
    end

    local prof = Bot.profile()
    setLabel("voc", "Vocação: " .. (prof and prof.name or "desconhecida"))

    local state
    if Bot.emergency then
        state = "EMERGÊNCIA (HP crítico)"
    elseif Bot.paused then
        state = "pausado"
    elseif Bot.fighting then
        state = "lutando" .. (Bot.lastTarget and (" — " .. Bot.lastTarget.name) or "")
    elseif Cave.mode == "refill" then
        state = "refill (wp " .. Cave.idx .. "/" .. #storage.wp_refill .. ")"
    else
        state = "caçando (wp " .. Cave.idx .. "/" .. math.max(#storage.wp_hunt, 1) .. ")"
    end
    setLabel("state", "Estado: " .. state)
    setLabel("route", "Rota: " .. #storage.wp_hunt .. " hunt / "
        .. #storage.wp_refill .. " refill")

    pcall(function()
        local exp = Bot.lp():getExperience()
        if not exp or exp <= 0 then return end
        if not sessionStartExp then
            sessionStartExp, sessionStartAt = exp, Bot.now()
            return
        end
        local hours = (Bot.now() - sessionStartAt) / 3600000
        if hours > 0.003 then  -- espera ~10 s antes de estimar
            local perHour = math.floor((exp - sessionStartExp) / hours)
            setLabel("exp", "Exp/h: " .. perHour)
        end
    end)
end)
