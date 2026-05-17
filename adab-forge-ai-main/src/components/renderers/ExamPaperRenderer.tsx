interface Props { content: string; streaming?: boolean }

export function ExamPaperRenderer({ content, streaming }: Props) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-xs uppercase tracking-[0.3em] text-[var(--gold)]">Punjab Board · Examination Paper</div>
        {streaming && (
          <span className="text-xs text-muted-foreground">✍️ generating…</span>
        )}
      </div>
      <div className="exam-paper">
        <div className="text-center" style={{ lineHeight: "39px" }}>
          <div className="urdu text-2xl font-bold text-ink">پرچہ امتحان</div>
          <div className="urdu text-sm text-muted-foreground">جماعت دہم · اردو</div>
        </div>
        <div
          className={`urdu mt-6 text-lg text-ink whitespace-pre-wrap ${streaming ? "cursor-blink" : ""}`}
          style={{ lineHeight: "39px" }}
        >
          {content}
        </div>
      </div>
    </div>
  );
}
