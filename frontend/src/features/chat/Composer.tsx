import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

type ComposerProps = {
  onSend: (content: string) => void;
  disabled?: boolean;
};

export function Composer({ onSend, disabled = false }: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const canSend = !disabled && value.trim().length > 0;

  const resizeTextarea = () => {
    const element = textareaRef.current;
    if (!element) {
      return;
    }

    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 200)}px`;
  };

  useEffect(() => {
    resizeTextarea();
  }, [value]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }

    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) {
        onSend(value.trim());
        setValue("");
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-transparent bg-[linear-gradient(180deg,rgba(11,16,32,0),rgba(11,16,32,0.76)_22%,rgba(11,16,32,0.92))] px-4 pb-5 pt-3 sm:px-7"
    >
      <div className="mx-auto w-full max-w-[720px]">
        <div className="flex items-end gap-3 rounded-2xl border border-[var(--border)] bg-[var(--glass)] p-2.5 shadow-[0_12px_45px_rgba(7,10,22,0.45)] backdrop-blur-xl transition focus-within:border-[rgba(121,161,255,0.62)] focus-within:shadow-[0_0_0_1px_rgba(121,161,255,0.35),0_14px_52px_rgba(8,12,26,0.58)]">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "Waiting for assistant..." : "Message DOTI..."}
            disabled={disabled}
            rows={1}
            className="chat-scroll max-h-[200px] min-h-[44px] flex-1 resize-none bg-transparent px-2.5 py-2 text-[15px] leading-7 text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="h-11 rounded-xl bg-[var(--accent)] px-4 text-base font-semibold text-white shadow-[0_10px_24px_rgba(95,145,255,0.36)] transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Send message"
          >
            →
          </button>
        </div>
        <p className="mt-2 px-1 text-[11px] tracking-wide text-[var(--text-muted)]">
          Enter to send, Shift+Enter for a new line
        </p>
      </div>
    </form>
  );
}
