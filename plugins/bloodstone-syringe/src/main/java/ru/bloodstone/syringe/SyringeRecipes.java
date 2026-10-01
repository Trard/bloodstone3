package ru.bloodstone.syringe;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.RecipeChoice;
import org.bukkit.inventory.ShapelessRecipe;
import org.bukkit.inventory.meta.PotionMeta;
import org.bukkit.potion.PotionType;

final class SyringeRecipes {
    private final SyringePlugin plugin;
    private final SyringeItems items;

    SyringeRecipes(SyringePlugin plugin, SyringeItems items) {
        this.plugin = plugin;
        this.items = items;
    }

    void scheduleRegistration() {
        Bukkit.getGlobalRegionScheduler().execute(plugin, () -> register(plugin.settings()));
    }

    void register(Settings settings) {
        NamespacedKey emptyKey = new NamespacedKey(plugin, "empty_syringe");
        NamespacedKey vaccineKey = new NamespacedKey(plugin, "vaccine");
        NamespacedKey refillKey = new NamespacedKey(plugin, "refill_syringe");

        ShapelessRecipe empty = new ShapelessRecipe(emptyKey, items.createEmpty(1, settings));
        empty.addIngredient(2, Material.GLASS).addIngredient(Material.IRON_INGOT);

        ItemStack water = new ItemStack(Material.POTION);
        PotionMeta waterMeta = (PotionMeta) water.getItemMeta();
        waterMeta.setBasePotionType(PotionType.WATER);
        water.setItemMeta(waterMeta);
        ShapelessRecipe vaccine = new ShapelessRecipe(vaccineKey, items.createVaccine());
        vaccine.addIngredient(new RecipeChoice.ExactChoice(water))
                .addIngredient(Material.SUGAR).addIngredient(Material.REDSTONE);

        // ExactChoice includes the PDC marker, so neither a regular carrot-on-a-stick
        // nor water/another potion can be used as a substitute for these ingredients.
        ShapelessRecipe refill = new ShapelessRecipe(refillKey, items.create(1, settings));
        refill.addIngredient(new RecipeChoice.ExactChoice(items.createEmpty(1, settings)))
                .addIngredient(new RecipeChoice.ExactChoice(items.createVaccine()));

        for (ShapelessRecipe recipe : new ShapelessRecipe[]{empty, vaccine, refill}) {
            Bukkit.removeRecipe(recipe.getKey());
            if (!Bukkit.addRecipe(recipe)) plugin.getLogger().warning("Не удалось зарегистрировать рецепт " + recipe.getKey());
        }
    }
}
