import type { Mode } from "@/types/rag";

const TUTOR_CHIPS = [
  { label: "خلاصہ", hint: "Summary" },
  { label: "خط", hint: "Letter" },
  { label: "کہانی", hint: "Story" },
  { label: "تشریح", hint: "Verse explain" },
  { label: "MCQs", hint: "Questions" },
];

const PAPER_CHIPS = [
  { label: "مکمل پرچہ", hint: "Full paper" },
  { label: "Q2 صرف", hint: "Only Q2" },
  { label: "نقل کریں", hint: "Mock test" },
];

export function PromptChips({
  mode,
  onPick,
}: {
  mode: Mode;
  onPick: (text: string) => void;
}) {
  const chips = mode === "tutor" ? TUTOR_CHIPS : PAPER_CHIPS;
  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((c) => (
        <button
          key={c.label}
          onClick={() => onPick(c.label)}
          className="group flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs transition hover:border-[var(--gold)] hover:bg-[var(--gold)]/10"
        >
          <span className="urdu text-sm text-primary">{c.label}</span>
          <span className="text-muted-foreground group-hover:text-foreground">· {c.hint}</span>
        </button>
      ))}
    </div>
  );
}
