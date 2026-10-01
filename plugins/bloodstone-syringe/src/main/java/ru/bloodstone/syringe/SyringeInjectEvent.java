package ru.bloodstone.syringe;

import org.bukkit.entity.Player;
import org.bukkit.event.Cancellable;
import org.bukkit.event.Event;
import org.bukkit.event.HandlerList;
import org.bukkit.potion.PotionEffect;
import org.jetbrains.annotations.NotNull;

/** Fired on the owning region before any dose/cooldown/item is committed. */
public final class SyringeInjectEvent extends Event implements Cancellable {
    private static final HandlerList HANDLERS = new HandlerList();
    private final Player injector;
    private final Player recipient;
    private final PotionEffect effect;
    private final boolean overdose;
    private boolean cancelled;

    public SyringeInjectEvent(Player injector, Player recipient, PotionEffect effect, boolean overdose) {
        this.injector = injector;
        this.recipient = recipient;
        this.effect = effect;
        this.overdose = overdose;
    }

    public Player getInjector() { return injector; }
    public Player getRecipient() { return recipient; }
    public PotionEffect getEffect() { return effect; }
    public boolean isOverdose() { return overdose; }
    @Override public boolean isCancelled() { return cancelled; }
    @Override public void setCancelled(boolean cancelled) { this.cancelled = cancelled; }
    @Override public @NotNull HandlerList getHandlers() { return HANDLERS; }
    public static HandlerList getHandlerList() { return HANDLERS; }
}
