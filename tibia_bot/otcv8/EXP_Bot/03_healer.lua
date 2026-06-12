-- 03_healer.lua
-- Cura por magia + poções, com gatilhos vindos do perfil da vocação.
-- Roda SEMPRE (mesmo pausado/emergência): curar nunca pode parar.
-- Exhausts respeitados: 1 s para magias de cura, 1 s para poções.

local nextPotionAt = 0

macro(100, "Healbot", function()
    if not Bot.ready() then return end
    Bot.verifyCasts()          -- fecha a verificação do cast anterior (modo trust)
    local prof = Bot.profile()
    if not prof then return end

    local hp = Bot.hpPercent()
    local now = Bot.now()

    -- ----- modo emergência (trava cavebot/loot em 05/06/07) -----
    if Bot.emergency then
        if hp >= CFG.emergency.resumeAboveHp then
            Bot.emergency = false
        elseif CFG.emergency.tryLogout then
            pcall(function() g_game.safeLogout() end)
        end
    elseif hp <= CFG.emergency.pauseBelowHp then
        Bot.emergency = true
    end

    -- ----- magias de cura (perfil lista da mais grave para a mais leve) -----
    -- só o gatilho de HP% é decidido aqui; level/mana/cooldown ficam a cargo
    -- do tryCast (que respeita o modo de gating e o backoff por magia)
    for _, h in ipairs(prof.heals or {}) do
        if hp <= h.below then
            if Bot.tryCast(h.words, "heal", h.level, h.mana) then break end
        end
    end

    -- ----- poções (grupo de exhaust próprio; HP tem prioridade) -----
    if now >= nextPotionAt and prof.potions then
        local hpPot, mpPot = prof.potions.hp, prof.potions.mana
        if hpPot and hp <= hpPot.below and Bot.countItem(hpPot.id) > 0 then
            Bot.useItemOn(hpPot.id, Bot.lp())
            nextPotionAt = now + 1050
        elseif mpPot and Bot.manaPercent() <= mpPot.below
                and Bot.countItem(mpPot.id) > 0 then
            Bot.useItemOn(mpPot.id, Bot.lp())
            nextPotionAt = now + 1050
        end
    end
end)
