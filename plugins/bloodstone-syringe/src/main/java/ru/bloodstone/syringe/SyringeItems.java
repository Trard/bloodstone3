package ru.bloodstone.syringe;

import io.papermc.paper.datacomponent.DataComponentTypes;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextDecoration;
import org.bukkit.Material;
import org.bukkit.Color;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.PotionMeta;
import org.bukkit.inventory.meta.components.CustomModelDataComponent;
import org.bukkit.inventory.meta.components.UseCooldownComponent;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.potion.PotionType;

import java.util.List;

final class SyringeItems {
    private final NamespacedKey marker;

    SyringeItems(NamespacedKey marker) { this.marker = marker; }

    ItemStack create(int count, Settings settings) {
        return createSyringe(count, settings, false);
    }

    ItemStack createEmpty(int count, Settings settings) {
        return createSyringe(count, settings, true);
    }

    private ItemStack createSyringe(int count, Settings settings, boolean empty) {
        ItemStack stack = new ItemStack(Material.CARROT_ON_A_STICK, count);
        ItemMeta meta = stack.getItemMeta();
        configure(meta, settings, empty);
        stack.setItemMeta(meta);
        // Minecraft forbids max_stack_size > 1 together with max_damage.
        stack.unsetData(DataComponentTypes.MAX_DAMAGE);
        stack.unsetData(DataComponentTypes.DAMAGE);
        return stack;
    }

    void configure(ItemMeta meta, Settings settings) {
        configure(meta, settings, false);
    }

    private void configure(ItemMeta meta, Settings settings, boolean empty) {
        meta.displayName(Component.text(empty ? "Пустой шприц" : settings.name(), empty ? NamedTextColor.GRAY : NamedTextColor.AQUA)
                .decoration(TextDecoration.ITALIC, false));
        meta.lore(null);
        configureCooldown(meta, settings);
        CustomModelDataComponent data = meta.getCustomModelDataComponent();
        data.setFloats(List.of((float) (empty ? settings.emptyCustomModelData() : settings.customModelData())));
        meta.setCustomModelDataComponent(data);
        meta.setItemModel(empty ? settings.emptyModel() : settings.model());
        meta.setMaxStackSize(64);
        meta.getPersistentDataContainer().set(marker, PersistentDataType.BYTE, empty ? (byte) 2 : (byte) 1);
    }

    boolean isSyringe(ItemStack stack) {
        return isKind(stack, Material.CARROT_ON_A_STICK, (byte) 1);
    }

    boolean isEmpty(ItemStack stack) { return isKind(stack, Material.CARROT_ON_A_STICK, (byte) 2); }

    boolean isVaccine(ItemStack stack) { return isKind(stack, Material.POTION, (byte) 3); }

    private boolean isKind(ItemStack stack, Material material, byte kind) {
        return stack != null && stack.getType() == material && stack.hasItemMeta()
                && Byte.valueOf(kind).equals(stack.getItemMeta().getPersistentDataContainer()
                .get(marker, PersistentDataType.BYTE));
    }

    ItemStack createVaccine() {
        ItemStack stack = new ItemStack(Material.POTION);
        PotionMeta meta = (PotionMeta) stack.getItemMeta();
        meta.setBasePotionType(PotionType.WATER);
        meta.setColor(Color.fromRGB(61, 214, 208));
        meta.displayName(Component.text("Вакцина", NamedTextColor.AQUA).decoration(TextDecoration.ITALIC, false));
        meta.getPersistentDataContainer().set(marker, PersistentDataType.BYTE, (byte) 3);
        stack.setItemMeta(meta);
        // A crafting ingredient, not a drinkable potion.
        stack.unsetData(DataComponentTypes.CONSUMABLE);
        return stack;
    }

    NamespacedKey cooldownGroup() { return marker; }

    /** Updates previously issued syringes without replacing their name or model. */
    boolean refresh(ItemStack stack, Settings settings) {
        if (!isSyringe(stack) && !isEmpty(stack)) return false;
        ItemMeta meta = stack.getItemMeta();
        UseCooldownComponent cooldown = meta.getUseCooldown();
        if (!meta.hasLore() && marker.equals(cooldown.getCooldownGroup())
                && cooldown.getCooldownSeconds() == settings.cooldownMillis() / 1000f) return false;
        meta.lore(null);
        configureCooldown(meta, settings);
        stack.setItemMeta(meta);
        return true;
    }

    private void configureCooldown(ItemMeta meta, Settings settings) {
        UseCooldownComponent cooldown = meta.getUseCooldown();
        cooldown.setCooldownGroup(marker);
        cooldown.setCooldownSeconds(settings.cooldownMillis() / 1000f);
        meta.setUseCooldown(cooldown);
    }
}
