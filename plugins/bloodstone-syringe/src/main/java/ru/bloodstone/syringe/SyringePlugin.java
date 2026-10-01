package ru.bloodstone.syringe;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import org.bukkit.Bukkit;
import org.bukkit.NamespacedKey;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.java.JavaPlugin;
import org.jetbrains.annotations.NotNull;

import java.io.File;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

public class SyringePlugin extends JavaPlugin {
    private volatile Settings settings;
    private SyringeItems items;
    private SyringeRecipes recipes;

    @Override public void onEnable() {
        saveDefaultConfig();
        try { loadSettings(); }
        catch (Exception error) {
            getLogger().severe("Ошибка config.yml: " + error.getMessage());
            getServer().getPluginManager().disablePlugin(this);
            return;
        }
        items = new SyringeItems(new NamespacedKey(this, "syringe"));
        getServer().getPluginManager().registerEvents(new InjectionListener(this, items), this);
        ItemRefreshListener refresher = new ItemRefreshListener(this, items);
        getServer().getPluginManager().registerEvents(refresher, this);
        Bukkit.getOnlinePlayers().forEach(refresher::schedule);
        recipes = new SyringeRecipes(this, items);
        recipes.scheduleRegistration();
        Objects.requireNonNull(getCommand("syringe")).setExecutor(this);
        Objects.requireNonNull(getCommand("syringe")).setTabCompleter(this);
        getLogger().info("Шприцы включены: Paper/Folia 1.21.11, CMD " + settings.customModelData());
    }

    Settings settings() { return settings; }

    // Replace the immutable snapshot only after all validation succeeds.
    private synchronized void loadSettings() throws Exception {
        YamlConfiguration yaml = new YamlConfiguration();
        File file = new File(getDataFolder(), "config.yml");
        yaml.load(file);
        boolean migrate = yaml.getInt("config-version", 1) < 2;
        if (migrate) {
            if (yaml.getDouble("injection.cooldown-seconds") == 1.5)
                yaml.set("injection.cooldown-seconds", 3.0);
            yaml.set("config-version", 2);
            yaml.set("item.consume", null);
        }
        Settings next = Settings.load(yaml);
        if (migrate) yaml.save(file);
        settings = next;
    }

    @Override public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                                       @NotNull String label, @NotNull String[] args) {
        if (!sender.hasPermission("bloodstonesyringe.admin")) {
            reply(sender, "Держите шприц в основной руке: ПКМ по игроку, Shift + ПКМ — в себя.");
            return true;
        }
        if (args.length == 1 && args[0].equalsIgnoreCase("reload")) {
            try { loadSettings(); recipes.scheduleRegistration(); reply(sender, "Настройки перезагружены."); }
            catch (Exception error) { reply(sender, "Конфиг отклонён: " + error.getMessage() + ". Прежние настройки сохранены."); }
            return true;
        }
        if (args.length >= 2 && args.length <= 3 && args[0].equalsIgnoreCase("give")) {
            Player target = Bukkit.getPlayerExact(args[1]);
            if (target == null) { reply(sender, "Игрок не найден в сети."); return true; }
            int count;
            try {
                count = args.length == 3 ? Integer.parseInt(args[2]) : 1;
                if (count < 1 || count > 2304) throw new NumberFormatException();
            } catch (NumberFormatException error) {
                reply(sender, "Количество: целое число от 1 до 2304.");
                return true;
            }
            int total = count;
            Settings snapshot = settings;
            // Console/player commands can originate in a different region.
            boolean scheduled = target.getScheduler().execute(this, () -> {
                if (!target.isOnline()) { reply(sender, "Игрок вышел до выдачи."); return; }
                for (int remaining = total; remaining > 0; remaining -= Math.min(64, remaining)) {
                    ItemStack stack = items.create(Math.min(64, remaining), snapshot);
                    for (ItemStack leftover : target.getInventory().addItem(stack).values())
                        target.getWorld().dropItemNaturally(target.getLocation(), leftover);
                }
                target.sendMessage(Component.text("Получено шприцев: " + total + ".", NamedTextColor.AQUA));
                if (sender != target) reply(sender, "Выдано " + total + " шприцев игроку " + target.getName() + ".");
            }, () -> reply(sender, "Игрок вышел до выдачи."), 1L);
            if (!scheduled) reply(sender, "Игрок сейчас недоступен.");
            return true;
        }
        reply(sender, "/syringe give <игрок> [количество] — выдать; /syringe reload — перечитать конфиг.");
        return true;
    }

    private void reply(CommandSender sender, String text) {
        Component message = Component.text("[Шприц] " + text, NamedTextColor.AQUA);
        if (sender instanceof Player player) {
            player.getScheduler().execute(this, () -> player.sendMessage(message), null, 1L);
        } else sender.sendMessage(message);
    }

    @Override public @NotNull List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                        @NotNull String alias, @NotNull String[] args) {
        if (!sender.hasPermission("bloodstonesyringe.admin")) return List.of();
        String prefix = args.length == 0 ? "" : args[args.length - 1].toLowerCase(Locale.ROOT);
        if (args.length == 1) return List.of("give", "reload").stream().filter(s -> s.startsWith(prefix)).toList();
        if (args.length == 2 && args[0].equalsIgnoreCase("give"))
            return Bukkit.getOnlinePlayers().stream().map(Player::getName)
                    .filter(s -> s.toLowerCase(Locale.ROOT).startsWith(prefix)).sorted().toList();
        if (args.length == 3 && args[0].equalsIgnoreCase("give"))
            return List.of("1", "8", "16", "64").stream().filter(s -> s.startsWith(prefix)).toList();
        return List.of();
    }
}
