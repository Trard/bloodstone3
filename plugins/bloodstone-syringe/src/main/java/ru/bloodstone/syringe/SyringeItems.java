package ru.bloodstone.syringe;

import io.papermc.paper.datacomponent.DataComponentTypes;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextDecoration;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.components.CustomModelDataComponent;
import org.bukkit.persistence.PersistentDataType;

import java.util.List;

final class SyringeItems {
    private final NamespacedKey marker;

    SyringeItems(NamespacedKey marker) { this.marker = marker; }

    ItemStack create(int count, Settings settings) {
        ItemStack stack = new ItemStack(Material.CARROT_ON_A_STICK, count);
        ItemMeta meta = stack.getItemMeta();
        configure(meta, settings);
        stack.setItemMeta(meta);
        // Minecraft forbids max_stack_size > 1 together with max_damage.
        stack.unsetData(DataComponentTypes.MAX_DAMAGE);
        stack.unsetData(DataComponentTypes.DAMAGE);
        return stack;
    }

    void configure(ItemMeta meta, Settings settings) {
        meta.displayName(Component.text(settings.name(), NamedTextColor.AQUA).decoration(TextDecoration.ITALIC, false));
        meta.lore(List.of(
                line("ПКМ по игроку — сделать укол", NamedTextColor.GRAY),
                line("Shift + ПКМ — вколоть себе", NamedTextColor.GRAY),
                line("Случайный эффект. Частые уколы вызывают передозировку!", NamedTextColor.RED)));
        CustomModelDataComponent data = meta.getCustomModelDataComponent();
        data.setFloats(List.of((float) settings.customModelData()));
        meta.setCustomModelDataComponent(data);
        meta.setItemModel(settings.model());
        meta.setMaxStackSize(64);
        meta.getPersistentDataContainer().set(marker, PersistentDataType.BYTE, (byte) 1);
    }

    boolean isSyringe(ItemStack stack) {
        return stack != null && stack.getType() == Material.CARROT_ON_A_STICK && stack.hasItemMeta()
                && Byte.valueOf((byte) 1).equals(stack.getItemMeta().getPersistentDataContainer()
                .get(marker, PersistentDataType.BYTE));
    }

    private Component line(String text, NamedTextColor color) {
        return Component.text(text, color).decoration(TextDecoration.ITALIC, false);
    }
}
