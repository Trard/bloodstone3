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
import org.bukkit.inventory.ShapelessRecipe;
import org.bukkit.inventory.meta.PotionMeta;
import org.bukkit.potion.PotionType;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.key.Key;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockbukkit.mockbukkit.MockBukkit;
import org.mockbukkit.mockbukkit.ServerMock;

import java.io.InputStreamReader;
import java.io.File;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
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
        assertEquals(3000, plugin.settings().cooldownMillis());
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
        assertFalse(meta.hasLore());
        assertEquals(3f, meta.getUseCooldown().getCooldownSeconds());
        assertEquals(items.cooldownGroup(), meta.getUseCooldown().getCooldownGroup());
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
        assertEquals(60, player.getCooldown(new NamespacedKey(plugin, "syringe")));
        assertEquals(0, player.getCooldown(Material.CARROT_ON_A_STICK));
        assertEquals(1, countEmpty(player));
        verify(player, never()).sendMessage(any(Component.class));
        listener.inject(player, player);
        assertEquals(7, player.getInventory().getItemInMainHand().getAmount());
        assertEquals(1, history(player).length);
        assertEquals(1, countEmpty(player));
        verify(player, never()).sendActionBar(any(Component.class));
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
        assertEquals(0, player.getCooldown(new NamespacedKey(plugin, "syringe")));
        assertEquals(0, countEmpty(player));
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
        Player actor = equip("Alice");
        Player target = equip("Bob");
        target.teleport(actor.getLocation());
        doReturn(true).when(actor).hasLineOfSight(target);
        listener().inject(actor, target);
        assertEquals(7, actor.getInventory().getItemInMainHand().getAmount());
        assertEquals(8, target.getInventory().getItemInMainHand().getAmount());
        assertNull(history(actor));
        assertEquals(1, history(target).length);
        verify(actor, never()).sendActionBar(any(Component.class));
        verify(target, never()).sendActionBar(any(Component.class));
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
        Player player = spy(server.addPlayer(name));
        // MockBukkit does not implement cooldown groups yet. Record the native API
        // calls without substituting the plugin's time/permission/item checks.
        Map<Key, Integer> cooldowns = new HashMap<>();
        doAnswer(call -> cooldowns.getOrDefault(call.getArgument(0), 0)).when(player).getCooldown(any(Key.class));
        doAnswer(call -> {
            cooldowns.put(call.getArgument(0), call.getArgument(1));
            return null;
        }).when(player).setCooldown(any(Key.class), anyInt());
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

    private SyringeItems items() { return new SyringeItems(new NamespacedKey(plugin, "syringe")); }

    private int countEmpty(Player player) {
        int total = 0;
        for (ItemStack stack : player.getInventory().getContents())
            if (items().isEmpty(stack)) total += stack.getAmount();
        return total;
    }

    @Test void lastFullSyringeBecomesEmptyInHandAndCannotInjectAgain() {
        Player player = equip("Alice");
        player.getInventory().setItemInMainHand(items().create(1, plugin.settings()));
        listener().inject(player, player);
        assertTrue(items().isEmpty(player.getInventory().getItemInMainHand()));
        assertEquals(1, countEmpty(player));
        listener().inject(player, player);
        assertEquals(1, history(player).length);
        assertEquals(1, countEmpty(player));
    }

    @Test void oldSyringesLoseLoreWithoutLosingTheirMarker() {
        Player player = equip("Alice");
        ItemStack stack = player.getInventory().getItemInMainHand();
        var meta = stack.getItemMeta();
        meta.lore(List.of(Component.text("Старый лор")));
        stack.setItemMeta(meta);
        player.getInventory().setItemInMainHand(stack);
        new ItemRefreshListener(plugin, items()).refresh(player);
        ItemStack refreshed = player.getInventory().getItemInMainHand();
        assertFalse(refreshed.getItemMeta().hasLore());
        assertTrue(items().isSyringe(refreshed));
        assertEquals(8, refreshed.getAmount());
    }

    @Test void threeRecipesProduceEmptyVaccineAndFullAndRejectCounterfeits() {
        new SyringeRecipes(plugin, items()).register(plugin.settings());
        var empty = (ShapelessRecipe) Bukkit.getRecipe(new NamespacedKey(plugin, "empty_syringe"));
        var vaccine = (ShapelessRecipe) Bukkit.getRecipe(new NamespacedKey(plugin, "vaccine"));
        var refill = (ShapelessRecipe) Bukkit.getRecipe(new NamespacedKey(plugin, "refill_syringe"));
        assertTrue(items().isEmpty(empty.getResult()));
        assertEquals(2, empty.getChoiceList().stream().filter(c -> c.test(new ItemStack(Material.GLASS))).count());
        assertEquals(1, empty.getChoiceList().stream().filter(c -> c.test(new ItemStack(Material.IRON_INGOT))).count());
        assertTrue(items().isVaccine(vaccine.getResult()));
        ItemStack water = new ItemStack(Material.POTION);
        PotionMeta meta = (PotionMeta) water.getItemMeta();
        meta.setBasePotionType(PotionType.WATER);
        water.setItemMeta(meta);
        assertTrue(vaccine.getChoiceList().getFirst().test(water));
        assertTrue(items().isSyringe(refill.getResult()));
        assertTrue(refill.getChoiceList().getFirst().test(items().createEmpty(1, plugin.settings())));
        assertTrue(refill.getChoiceList().get(1).test(items().createVaccine()));
        assertFalse(refill.getChoiceList().getFirst().test(new ItemStack(Material.CARROT_ON_A_STICK)));
        assertFalse(refill.getChoiceList().getFirst().test(items().create(1, plugin.settings())));
        assertFalse(refill.getChoiceList().get(1).test(water));
    }

    @Test void legacyDefaultCooldownMigratesToThreeSeconds() throws Exception {
        File file = new File(plugin.getDataFolder(), "config.yml");
        YamlConfiguration legacy = defaults();
        legacy.set("config-version", null);
        legacy.set("injection.cooldown-seconds", 1.5);
        legacy.save(file);
        server.dispatchCommand(server.getConsoleSender(), "syringe reload");
        assertEquals(3000, plugin.settings().cooldownMillis());
        assertEquals(3.0, YamlConfiguration.loadConfiguration(file).getDouble("injection.cooldown-seconds"));
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
