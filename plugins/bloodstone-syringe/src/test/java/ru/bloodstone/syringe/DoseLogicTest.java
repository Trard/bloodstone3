package ru.bloodstone.syringe;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class DoseLogicTest {
    @Test void fourthDoseStartsOverdoseAndFurtherDosesStayBounded() {
        long[] history = null;
        for (int shot = 1; shot <= 100; shot++) {
            history = DoseLogic.add(history, shot * 100L, 60000, 4);
            assertEquals(Math.min(shot, 4), history.length);
            assertEquals(shot >= 4, history.length >= 4);
        }
    }

    @Test void exactSixtySecondBoundaryExpires() {
        assertArrayEquals(new long[]{2001, 61000}, DoseLogic.add(new long[]{1000, 2001}, 61000, 60000, 4));
    }

    @Test void expiredHistoryAndFutureClockValuesAreDiscarded() {
        assertArrayEquals(new long[]{90000}, DoseLogic.add(new long[]{1000, 100000}, 90000, 60000, 4));
    }

    @Test void rollingWindowDoesNotExtendOlderDosesWhenAnotherShotArrives() {
        long[] history = {1000, 2000, 3000, 59000};
        assertEquals(4, DoseLogic.add(history, 61000, 60000, 4).length);
        assertArrayEquals(new long[]{59000, 63000}, DoseLogic.add(history, 63000, 60000, 4));
    }

    @Test void probabilitiesHaveExactBoundaries() {
        int normal = 0, overdose = 0;
        for (int bucket = 0; bucket < 10000; bucket++) {
            double roll = bucket / 10000.0;
            if (DoseLogic.negative(roll, false, .5, .75)) normal++;
            if (DoseLogic.negative(roll, true, .5, .75)) overdose++;
        }
        assertEquals(5000, normal);
        assertEquals(7500, overdose);
        assertFalse(DoseLogic.negative(.75, true, .5, .75));
    }
}
