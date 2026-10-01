package ru.bloodstone.syringe;

import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityPickupItemEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.event.player.PlayerItemHeldEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.inventory.ItemStack;

/** Migrates existing inventory items on their player's owning region. */
final class ItemRefreshListener implements Listener {
    private final SyringePlugin plugin;
    private final SyringeItems items;

    ItemRefreshListener(SyringePlugin plugin, SyringeItems items) {
        this.plugin = plugin;
        this.items = items;
    }

    void schedule(Player player) {
        player.getScheduler().execute(plugin, () -> refresh(player), null, 1L);
    }

    void refresh(Player player) {
        Settings settings = plugin.settings();
        for (int slot = 0; slot < player.getInventory().getSize(); slot++) {
            ItemStack stack = player.getInventory().getItem(slot);
            if (items.refresh(stack, settings)) player.getInventory().setItem(slot, stack);
        }
        ItemStack cursor = player.getItemOnCursor();
        if (items.refresh(cursor, settings)) player.setItemOnCursor(cursor);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onJoin(PlayerJoinEvent event) { schedule(event.getPlayer()); }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onHeld(PlayerItemHeldEvent event) { schedule(event.getPlayer()); }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onClick(InventoryClickEvent event) {
        if (event.getWhoClicked() instanceof Player player) schedule(player);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onDrag(InventoryDragEvent event) {
        if (event.getWhoClicked() instanceof Player player) schedule(player);
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onPickup(EntityPickupItemEvent event) {
        if (event.getEntity() instanceof Player player) schedule(player);
    }
}
