import { motion } from "framer-motion";

interface MCQ {
  question: string;
  options: string[];
  answer?: number;
}

function parse(content: string): MCQ[] {
  // Try JSON first
  try {
    const j = JSON.parse(content);
    if (Array.isArray(j)) return j;
    if (Array.isArray(j.questions)) return j.questions;
  } catch {}

  // Fallback: simple text parse "1. question\n- opt\n- opt"
  const blocks = content.split(/\n\s*\n/).filter(Boolean);
  return blocks.map((b) => {
    const lines = b.split("\n").map((l) => l.trim()).filter(Boolean);
    return {
      question: lines[0] ?? "",
      options: lines.slice(1).map((l) => l.replace(/^[-•○◯]\s*/, "")),
    };
  });
}

export function MCQRenderer({ content }: { content: string }) {
  const items = parse(content);
  return (
    <div className="space-y-4">
      {items.map((q, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className="rounded-xl border border-border bg-card p-5 shadow-[var(--shadow-soft)]"
        >
          <div className="mb-3 flex items-center gap-2">
            <span className="rounded-md bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
              سوال {i + 1}
            </span>
          </div>
          <p className="urdu text-lg text-foreground">{q.question}</p>
          <div className="mt-4 space-y-2">
            {q.options.map((opt, j) => (
              <button
                key={j}
                className="group flex w-full items-center gap-3 rounded-lg border border-border bg-background px-4 py-3 text-right transition hover:border-primary hover:bg-primary/5"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-border text-xs font-semibold text-muted-foreground group-hover:border-primary group-hover:text-primary">
                  {String.fromCharCode(0x0627 + j)}
                </span>
                <span className="urdu flex-1">{opt}</span>
              </button>
            ))}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
