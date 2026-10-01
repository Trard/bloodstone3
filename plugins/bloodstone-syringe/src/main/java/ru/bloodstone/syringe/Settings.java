package ru.bloodstone.syringe;

import org.bukkit.NamespacedKey;
import org.bukkit.Registry;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

record Settings(int customModelData, NamespacedKey model, String name, boolean consume,
                long cooldownMillis, double distance, boolean respectPvp, boolean particles, boolean sounds,
                double negativeChance, int threshold, long windowMillis, double overdoseNegativeChance,
                boolean clearOnDeath, List<EffectSpec> positive, List<EffectSpec> negative) {

    record EffectSpec(PotionEffectType type, int ticks, int amplifier, int overdoseTicks, int overdoseAmplifier) {
        PotionEffect create(boolean overdose) {
            return new PotionEffect(type, overdose ? overdoseTicks : ticks,
                    overdose ? overdoseAmplifier : amplifier, false, true, true);
        }
    }

    static Settings load(FileConfiguration config) {
        NamespacedKey model = NamespacedKey.fromString(config.getString("item.model", ""));
        require(model != null, "item.model: нужен namespace:path");
        int data = integer(config.get("item.custom-model-data"), 1, 16_777_216, "item.custom-model-data");
        String name = config.getString("item.name", "Шприц с вакциной");
        require(!name.isBlank(), "item.name не может быть пустым");
        return new Settings(data, model, name, config.getBoolean("item.consume", true),
                Math.round(number(config.get("injection.cooldown-seconds"), 0.1, 60, "cooldown") * 1000),
                number(config.get("injection.max-distance"), 0.5, 6, "max-distance"),
                config.getBoolean("injection.respect-world-pvp", true),
                config.getBoolean("injection.particles", true), config.getBoolean("injection.sounds", true),
                number(config.get("injection.negative-chance"), 0, 1, "negative-chance"),
                integer(config.get("overdose.threshold"), 2, 100, "overdose.threshold"),
                Math.round(number(config.get("overdose.window-seconds"), 1, 3600, "overdose.window-seconds") * 1000),
                number(config.get("overdose.negative-chance"), 0, 1, "overdose.negative-chance"),
                config.getBoolean("overdose.clear-on-death", true),
                effects(config, "positive"), effects(config, "negative"));
    }

    private static List<EffectSpec> effects(FileConfiguration config, String group) {
        List<EffectSpec> effects = new ArrayList<>();
        for (Map<?, ?> entry : config.getMapList("effects." + group)) {
            Object typeId = entry.get("type");
            NamespacedKey key = typeId instanceof String text ? NamespacedKey.fromString(text) : null;
            PotionEffectType type = key == null ? null : Registry.MOB_EFFECT.get(key);
            require(type != null, "Неизвестный эффект: " + typeId);
            int ticks = integer(entry.get("seconds"), 1, 3600, group + ".seconds") * 20;
            int level = integer(entry.get("level"), 1, 10, group + ".level") - 1;
            int overdoseTicks = entry.containsKey("overdose-seconds")
                    ? integer(entry.get("overdose-seconds"), 1, 3600, group + ".overdose-seconds") * 20 : ticks;
            int overdoseLevel = entry.containsKey("overdose-level")
                    ? integer(entry.get("overdose-level"), 1, 10, group + ".overdose-level") - 1 : level;
            effects.add(new EffectSpec(type, ticks, level, overdoseTicks, overdoseLevel));
        }
        require(!effects.isEmpty(), "effects." + group + " должен содержать хотя бы один эффект");
        return List.copyOf(effects);
    }

    private static int integer(Object value, int min, int max, String path) {
        double number = number(value, min, max, path);
        require(number == Math.rint(number), path + " должен быть целым числом");
        return (int) number;
    }

    private static double number(Object value, double min, double max, String path) {
        require(value instanceof Number, path + " должен быть числом");
        double number = ((Number) value).doubleValue();
        require(Double.isFinite(number) && number >= min && number <= max,
                path + " должен быть от " + min + " до " + max);
        return number;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
