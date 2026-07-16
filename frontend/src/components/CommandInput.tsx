import { useRef, useState, type KeyboardEvent } from "react";

import { complete } from "../terminal/autocomplete";
import { CommandHistory } from "../terminal/commandHistory";

/**
 * The command line. Handles submission, history navigation (Up/Down), and Tab
 * autocomplete. Kept deliberately simple and keyboard-first for accessibility.
 */
export function CommandInput({
  onSubmit,
  disabled,
}: {
  onSubmit: (text: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const [hint, setHint] = useState<string[]>([]);
  const history = useRef(new CommandHistory());

  const submit = () => {
    const text = value.trim();
    if (!text) return;
    history.current.add(text);
    onSubmit(text);
    setValue("");
    setHint([]);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    switch (event.key) {
      case "Enter":
        submit();
        break;
      case "ArrowUp": {
        event.preventDefault();
        const prev = history.current.previous();
        if (prev !== null) setValue(prev);
        break;
      }
      case "ArrowDown": {
        event.preventDefault();
        const next = history.current.next();
        if (next !== null) setValue(next);
        break;
      }
      case "Tab": {
        event.preventDefault();
        const options = complete(value);
        if (options.length === 1) {
          const words = value.split(/\s+/);
          words[words.length - 1] = options[0];
          setValue(words.join(" ") + " ");
          setHint([]);
        } else {
          setHint(options);
        }
        break;
      }
      default:
        break;
    }
  };

  return (
    <div className="command-input">
      {hint.length > 1 && <div className="autocomplete-hint dim">{hint.join("   ")}</div>}
      <div className="input-row">
        <span className="prompt-mark">&gt;</span>
        <input
          type="text"
          autoFocus
          spellCheck={false}
          autoComplete="off"
          disabled={disabled}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type your action..."
          aria-label="Command input"
        />
      </div>
    </div>
  );
}
