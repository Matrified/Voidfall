/**
 * A bounded command history with cursor-style navigation, mirroring how a shell behaves:
 * pressing Up walks toward older entries, Down walks back toward the present, and once
 * you step past the newest entry the input clears.
 */

const MAX_ENTRIES = 100;

export class CommandHistory {
  private entries: string[] = [];
  private cursor = 0; // points one past the newest entry when "at the present"

  add(command: string): void {
    const trimmed = command.trim();
    if (!trimmed) return;
    this.entries.push(trimmed);
    if (this.entries.length > MAX_ENTRIES) this.entries.shift();
    this.cursor = this.entries.length;
  }

  /** Returns the previous (older) entry, or null if history is empty. */
  previous(): string | null {
    if (this.entries.length === 0) return null;
    this.cursor = Math.max(0, this.cursor - 1);
    return this.entries[this.cursor];
  }

  /** Returns the next (newer) entry, or "" when stepping past the newest. */
  next(): string | null {
    if (this.entries.length === 0) return null;
    this.cursor = Math.min(this.entries.length, this.cursor + 1);
    return this.cursor === this.entries.length ? "" : this.entries[this.cursor];
  }
}
