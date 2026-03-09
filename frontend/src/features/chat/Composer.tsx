import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

type ComposerProps = {
  onSend: (content: string) => void;
  disabled?: boolean;
};

export function Composer({ onSend, disabled = false }: ComposerProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const canSend = !disabled && value.trim().length > 0;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="shrink-0 border-t border-[var(--border)] px-4 pb-4 pt-3 sm:px-6">
      <div className="mx-auto flex max-w-[720px] items-end gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-2 transition-colors focus-within:border-[var(--accent)]/50">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Waiting..." : "Message DOTI..."}
          disabled={disabled}
          rows={1}
          className="chat-scroll max-h-[200px] min-h-[40px] flex-1 resize-none bg-transparent px-2 py-1.5 text-[15px] leading-relaxed text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-white transition hover:bg-[var(--accent-hover)] disabled:opacity-30"
          aria-label="Send"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8h12M9 3l5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
      <p className="mt-1.5 text-center text-[11px] text-[var(--text-muted)]">
        Enter to send · Shift+Enter for newline
      </p>
    </form>
  );
}
