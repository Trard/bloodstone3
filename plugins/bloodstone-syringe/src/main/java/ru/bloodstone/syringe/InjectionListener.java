package ru.bloodstone.syringe;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.NamespacedKey;
import org.bukkit.Particle;
import org.bukkit.Sound;
import org.bukkit.SoundCategory;
import org.bukkit.entity.Player;
import org.bukkit.event.Event;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerInteractAtEntityEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.persistence.PersistentDataContainer;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.potion.PotionEffect;

import java.util.List;
import java.util.Locale;
import java.util.concurrent.ThreadLocalRandom;

final class InjectionListener implements Listener {
    private final SyringePlugin plugin;
    private final SyringeItems items;
    private final NamespacedKey dosesKey;
    private final NamespacedKey cooldownKey;

    InjectionListener(SyringePlugin plugin, SyringeItems items) {
        this.plugin = plugin;
        this.items = items;
        dosesKey = new NamespacedKey(plugin, "dose_history");
        cooldownKey = new NamespacedKey(plugin, "last_injection");
    }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onEntity(PlayerInteractEntityEvent event) { interactWithEntity(event); }

    @EventHandler(priority = EventPriority.HIGHEST, ignoreCancelled = true)
    public void onEntityAt(PlayerInteractAtEntityEvent event) { interactWithEntity(event); }

    private void interactWithEntity(PlayerInteractEntityEvent event) {
        Player actor = event.getPlayer();
        if (!items.isSyringe(actor.getInventory().getItem(event.getHand()))) return;
        event.setCancelled(true);
        if (event.getHand() != EquipmentSlot.HAND) return;
        if (actor.isSneaking()) inject(actor, actor);
        else if (event.getRightClicked() instanceof Player target) inject(actor, target);
    }

    // Air clicks with a non-usable item arrive pre-cancelled by vanilla prediction.
    // For block clicks DENY is respected so claim plugins can veto interaction.
    @EventHandler(priority = EventPriority.HIGHEST)
    public void onClick(PlayerInteractEvent event) {
        if (event.getAction() != Action.RIGHT_CLICK_AIR && event.getAction() != Action.RIGHT_CLICK_BLOCK) return;
        if (!items.isSyringe(event.getItem())) return;
        boolean denied = event.getAction() == Action.RIGHT_CLICK_BLOCK
                && event.useItemInHand() == Event.Result.DENY;
        event.setUseItemInHand(Event.Result.DENY);
        event.setUseInteractedBlock(Event.Result.DENY);
        if (denied || event.getHand() != EquipmentSlot.HAND) return;
        if (event.getPlayer().isSneaking()) inject(event.getPlayer(), event.getPlayer());
    }

    void inject(Player actor, Player target) {
        Settings settings = plugin.settings();
        if (!actor.hasPermission("bloodstonesyringe.use")) {
            hint(actor, "Нет права использовать шприц.");
            return;
        }
        // Close players normally share a ticking region. Never read a foreign
        // entity's location/inventory, even while it is transferring regions.
        if (!Bukkit.isOwnedByCurrentRegion(actor) || !Bukkit.isOwnedByCurrentRegion(target)) {
            hint(actor, "Игрок перемещается между регионами. Повторите укол.");
            return;
        }
        if (!valid(actor) || !valid(target)) return;
        boolean self = actor == target;
        if (!self) {
            if (!actor.getWorld().equals(target.getWorld())
                    || actor.getLocation().distanceSquared(target.getLocation()) > settings.distance() * settings.distance()
                    || !actor.hasLineOfSight(target)) {
                hint(actor, "Подойдите ближе к игроку.");
                return;
            }
            if (settings.respectPvp() && !actor.getWorld().getPVP()) {
                hint(actor, "В этом мире уколы другим игрокам отключены вместе с PvP.");
                return;
            }
        }
        ItemStack held = actor.getInventory().getItemInMainHand();
        if (!items.isSyringe(held)) return;
        long now = System.currentTimeMillis();
        PersistentDataContainer actorData = actor.getPersistentDataContainer();
        long last = actorData.getOrDefault(cooldownKey, PersistentDataType.LONG, 0L);
        long elapsed = now - last;
        if (elapsed >= 0 && elapsed < settings.cooldownMillis()) {
            hint(actor, String.format(Locale.ROOT, "Следующий укол через %.1f сек.", (settings.cooldownMillis() - elapsed) / 1000.0));
            return;
        }
        PersistentDataContainer targetData = target.getPersistentDataContainer();
        long[] doses = DoseLogic.add(targetData.get(dosesKey, PersistentDataType.LONG_ARRAY),
                now, settings.windowMillis(), settings.threshold());
        boolean overdose = doses.length >= settings.threshold();
        ThreadLocalRandom random = ThreadLocalRandom.current();
        boolean negative = DoseLogic.negative(random.nextDouble(), overdose,
                settings.negativeChance(), settings.overdoseNegativeChance());
        List<Settings.EffectSpec> pool = negative ? settings.negative() : settings.positive();
        PotionEffect effect = pool.get(random.nextInt(pool.size())).create(overdose);
        SyringeInjectEvent injection = new SyringeInjectEvent(actor, target, effect, overdose);
        if (!injection.callEvent()) return;
        // An event listener may teleport/remove a player or replace the held item.
        if (!Bukkit.isOwnedByCurrentRegion(actor) || !Bukkit.isOwnedByCurrentRegion(target)
                || !valid(actor) || !valid(target)) return;
        held = actor.getInventory().getItemInMainHand();
        if (!items.isSyringe(held)) return;
        if (!target.addPotionEffect(effect)) {
            hint(actor, "Эффект отклонён или уже действует более сильный. Шприц сохранён.");
            return;
        }
        targetData.set(dosesKey, PersistentDataType.LONG_ARRAY, doses);
        actorData.set(cooldownKey, PersistentDataType.LONG, now);
        if (settings.consume()) {
            if (held.getAmount() <= 1) actor.getInventory().setItemInMainHand(null);
            else held.setAmount(held.getAmount() - 1);
        }
        actor.swingMainHand();
        playFeedback(target, overdose, negative, settings);
        NamedTextColor color = negative ? NamedTextColor.RED : NamedTextColor.GREEN;
        Component result = Component.text(overdose ? "Передозировка! " : "Укол: ", color)
                .append(Component.translatable(effect.getType().translationKey()))
                .append(Component.text(" " + (effect.getAmplifier() + 1) + " · " + effect.getDuration() / 20 + " сек."));
        target.sendActionBar(result);
        target.sendMessage(Component.text("[Шприц] ", NamedTextColor.AQUA).append(result));
        if (!self) actor.sendActionBar(Component.text("Укол игроку " + target.getName() + ": ", NamedTextColor.AQUA).append(result));
    }

    private boolean valid(Player player) {
        return player.isOnline() && !player.isDead() && player.getGameMode() != GameMode.SPECTATOR;
    }

    private void playFeedback(Player target, boolean overdose, boolean negative, Settings settings) {
        Location location = target.getLocation().add(0, 1, 0);
        if (settings.sounds()) {
            target.getWorld().playSound(location, Sound.BLOCK_TRIPWIRE_CLICK_ON, SoundCategory.PLAYERS, 0.7f, 1.7f);
            target.getWorld().playSound(location, Sound.BLOCK_BREWING_STAND_BREW, SoundCategory.PLAYERS, 0.6f, 1.6f);
            if (overdose) target.getWorld().playSound(location, Sound.ENTITY_ELDER_GUARDIAN_CURSE, SoundCategory.PLAYERS, 0.4f, 1.7f);
        }
        if (settings.particles()) {
            target.getWorld().spawnParticle(negative ? Particle.SMOKE : Particle.HAPPY_VILLAGER,
                    location, overdose ? 24 : 10, 0.25, 0.35, 0.25, 0.015);
            target.getWorld().spawnParticle(Particle.CRIT, location, 6, 0.15, 0.15, 0.15, 0.05);
        }
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDeath(PlayerDeathEvent event) {
        if (plugin.settings().clearOnDeath()) event.getEntity().getPersistentDataContainer().remove(dosesKey);
    }

    private void hint(Player player, String text) { player.sendActionBar(Component.text(text, NamedTextColor.YELLOW)); }
}
