-- 04_support.lua
-- Rotinas de suporte: comida e anti-idle (não levar kick por inatividade).

macro(60000, "Comer comida", function()
    if not Bot.ready() then return end
    for _, id in ipairs(CFG.food or {}) do
        if Bot.countItem(id) > 0 then
            -- duas mordidas por ciclo; "You are full" é inofensivo
            Bot.useItem(id)
            Bot.schedule(400, function() Bot.useItem(id) end)
            break
        end
    end
end)

local lastDir = 0
macro(240000, "Anti-idle", function()
    if not Bot.ready() then return end
    lastDir = (lastDir + 1) % 4
    pcall(function() g_game.turn(lastDir) end)
end)
