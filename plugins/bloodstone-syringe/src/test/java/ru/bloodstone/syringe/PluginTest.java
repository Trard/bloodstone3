package ru.bloodstone.syringe;

import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.inventory.ItemStack;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Objects;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class PluginTest {
    ServerMock server;
    SyringePlugin plugin;

    @BeforeEach void setup() {
        server = MockBukkit.mock();
        plugin = MockBukkit.load(SyringePlugin.class);
    }

    @AfterEach void cleanup() { MockBukkit.unmock(); }

    @Test void loadsDefaultsAndCreatesMarkedModernItem() {
        assertTrue(plugin.isEnabled());
        assertEquals(4, plugin.settings().threshold());
        assertEquals(.75, plugin.settings().overdoseNegativeChance());
        SyringeItems items = new SyringeItems(new NamespacedKey(plugin, "syringe"));
        ItemStack stack = items.create(8, plugin.settings());
        assertTrue(items.isSyringe(stack));
        assertEquals(8, stack.getAmount());
        assertEquals(64, stack.getMaxStackSize());
        // MockBukkit's damageable ItemMeta copy drops CMD and item_model.
        // Verify the configured components before its mock inventory copy.
        var meta = stack.getItemMeta();
        items.configure(meta, plugin.settings());
        assertEquals(21011f, meta.getCustomModelDataComponent().getFloats().getFirst());
        assertEquals("bloodstone:tools/syringe/default/syringe", meta.getItemModel().toString());
        assertFalse(items.isSyringe(new ItemStack(Material.CARROT_ON_A_STICK)));
        assertFalse(items.isSyringe(null));
    }

    @Test void selfInjectionConsumesExactlyOneAndDuplicateEventDoesNothing() {
        Player player = equip("Alice");
        InjectionListener listener = listener();
        listener.inject(player, player);
        assertEquals(7, player.getInventory().getItemInMainHand().getAmount());
        assertEquals(1, player.getActivePotionEffects().size());
        assertEquals(1, history(player).length);
        listener.inject(player, player);
        assertEquals(7, player.getInventory().getItemInMainHand().getAmount());
        assertEquals(1, history(player).length);
    }

    @Test void sneakAirClickWorksEvenWhenVanillaPredictsNoAction() {
        Player player = equip("Alice");
        player.setSneaking(true);
        var click = new PlayerInteractEvent(player, Action.RIGHT_CLICK_AIR,
                player.getInventory().getItemInMainHand(), null, null, EquipmentSlot.HAND);
        click.setCancelled(true);
        server.getPluginManager().callEvent(click);
        assertEquals(7, player.getInventory().getItemInMainHand().getAmount());
    }

    @Test void offhandAndPlainAirClicksDoNotInject() {
        Player player = equip("Alice");
        var click = new PlayerInteractEvent(player, Action.RIGHT_CLICK_AIR,
                player.getInventory().getItemInMainHand(), null, null, EquipmentSlot.HAND);
        server.getPluginManager().callEvent(click);
        player.setSneaking(true);
        click = new PlayerInteractEvent(player, Action.RIGHT_CLICK_AIR,
                player.getInventory().getItemInMainHand(), null, null, EquipmentSlot.OFF_HAND);
        server.getPluginManager().callEvent(click);
        assertEquals(8, player.getInventory().getItemInMainHand().getAmount());
        assertNull(history(player));
    }

    @Test void cancelledInjectionCostsNothing() {
        Player player = equip("Alice");
        server.getPluginManager().registerEvents(new Listener() {
            @EventHandler public void cancel(SyringeInjectEvent event) { event.setCancelled(true); }
        }, plugin);
        listener().inject(player, player);
        assertEquals(8, player.getInventory().getItemInMainHand().getAmount());
        assertNull(history(player));
        assertTrue(player.getActivePotionEffects().isEmpty());
    }

    @Test void fourthDoseUsesOverdoseProfile() {
        Player player = equip("Alice");
        long now = System.currentTimeMillis();
        player.getPersistentDataContainer().set(new NamespacedKey(plugin, "dose_history"),
                PersistentDataType.LONG_ARRAY, new long[]{now - 6000, now - 4000, now - 2000});
        boolean[] overdose = {false};
        server.getPluginManager().registerEvents(new Listener() {
            @EventHandler public void capture(SyringeInjectEvent event) { overdose[0] = event.isOverdose(); }
        }, plugin);
        listener().inject(player, player);
        assertTrue(overdose[0]);
        assertEquals(4, history(player).length);
    }

    @Test void recipientReceivesDoseAndInjectorPays() {
        Player actor = spy(equip("Alice"));
        Player target = equip("Bob");
        target.teleport(actor.getLocation());
        doReturn(true).when(actor).hasLineOfSight(target);
        listener().inject(actor, target);
        assertEquals(7, actor.getInventory().getItemInMainHand().getAmount());
        assertEquals(8, target.getInventory().getItemInMainHand().getAmount());
        assertNull(history(actor));
        assertEquals(1, history(target).length);
    }

    @Test void foreignFoliaRegionIsRejectedWithoutAccessingTargetState() {
        Player actor = equip("Alice");
        Player target = mock(Player.class);
        try (var bukkit = mockStatic(Bukkit.class, CALLS_REAL_METHODS)) {
            bukkit.when(() -> Bukkit.isOwnedByCurrentRegion(target)).thenReturn(false);
            listener().inject(actor, target);
            verifyNoInteractions(target);
        }
        assertEquals(8, actor.getInventory().getItemInMainHand().getAmount());
    }

    @Test void spectatorCannotInject() {
        Player player = equip("Alice");
        player.setGameMode(GameMode.SPECTATOR);
        listener().inject(player, player);
        assertEquals(8, player.getInventory().getItemInMainHand().getAmount());
    }

    @Test void cancelledEntityInteractionDoesNotInject() {
        Player player = equip("Alice");
        player.setSneaking(true);
        var event = new PlayerInteractEntityEvent(player, player, EquipmentSlot.HAND);
        event.setCancelled(true);
        server.getPluginManager().callEvent(event);
        assertEquals(8, player.getInventory().getItemInMainHand().getAmount());
    }

    private Player equip(String name) {
        Player player = server.addPlayer(name);
        player.getWorld().setPVP(true);
        player.getInventory().setItemInMainHand(new SyringeItems(new NamespacedKey(plugin, "syringe")).create(8, plugin.settings()));
        return player;
    }

    private long[] history(Player player) {
        return player.getPersistentDataContainer().get(new NamespacedKey(plugin, "dose_history"), PersistentDataType.LONG_ARRAY);
    }

    private InjectionListener listener() {
        return new InjectionListener(plugin, new SyringeItems(new NamespacedKey(plugin, "syringe")));
    }

    @Test void invalidConfigIsRejected() {
        YamlConfiguration yaml = defaults();
        yaml.set("overdose.negative-chance", 1.1);
        assertThrows(IllegalArgumentException.class, () -> Settings.load(yaml));
        YamlConfiguration emptyPool = defaults();
        emptyPool.set("effects.positive", java.util.List.of());
        assertThrows(IllegalArgumentException.class, () -> Settings.load(emptyPool));
    }

    private YamlConfiguration defaults() {
        return YamlConfiguration.loadConfiguration(new InputStreamReader(
                Objects.requireNonNull(getClass().getResourceAsStream("/config.yml")), StandardCharsets.UTF_8));
    }
}
