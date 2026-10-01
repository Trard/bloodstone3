package ru.bloodstone.syringe;

import java.util.Arrays;

/** Pure, bounded rolling window. Timestamps are persisted on the recipient. */
final class DoseLogic {
    private DoseLogic() {}

    static long[] add(long[] previous, long now, long windowMillis, int threshold) {
        long[] active = Arrays.stream(previous == null ? new long[0] : previous)
                .filter(time -> time <= now && now - time < windowMillis).sorted().toArray();
        int keep = Math.min(active.length, threshold - 1);
        long[] result = new long[keep + 1];
        System.arraycopy(active, active.length - keep, result, 0, keep);
        result[keep] = now;
        return result;
    }

    static boolean negative(double roll, boolean overdose, double normalChance, double overdoseChance) {
        return roll < (overdose ? overdoseChance : normalChance);
    }
}
