import { useState, useRef, useEffect } from "react";
import { Send, Square } from "lucide-react";
import { PromptChips } from "./PromptChips";
import type { Mode } from "@/types/rag";

export function ChatInput({
  mode,
  onSend,
  onStop,
  busy,
}: {
  mode: Mode;
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = Math.min(ref.current.scrollHeight, 200) + "px";
    }
  }, [value]);

  const submit = () => {
    const v = value.trim();
    if (!v || busy) return;
    onSend(v);
    setValue("");
  };

  const placeholder =
    mode === "tutor"
      ? "اپنا سوال یہاں لکھیں… (e.g. علامہ اقبال کی تشریح)"
      : "پرچہ کی تفصیلات لکھیں… (e.g. 10th class full paper)";

  return (
    <div className="mx-auto w-full max-w-4xl space-y-3 px-4 pb-6">
      <PromptChips mode={mode} onPick={(t) => setValue((v) => (v ? `${v} ${t}` : t))} />

      <div className="relative rounded-2xl border border-border bg-card shadow-[var(--shadow-soft)] focus-within:border-primary focus-within:shadow-[var(--shadow-emerald)]">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          rows={1}
          dir="auto"
          className="urdu max-h-[200px] min-h-[56px] w-full resize-none bg-transparent px-5 py-4 text-base text-foreground placeholder:text-muted-foreground placeholder:font-sans focus:outline-none"
        />
        <div className="flex items-center justify-between px-3 pb-2">
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
            {mode === "tutor" ? "Tutor mode" : "Paper mode"} · Shift+Enter for newline
          </span>
          {busy ? (
            <button
              onClick={onStop}
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-destructive text-destructive-foreground transition hover:opacity-90"
            >
              <Square className="h-3.5 w-3.5" fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={!value.trim()}
              className="flex h-9 items-center gap-2 rounded-lg bg-[var(--gradient-emerald)] px-3 text-sm font-medium text-primary-foreground shadow-[var(--shadow-emerald)] transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send className="h-3.5 w-3.5" />
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
