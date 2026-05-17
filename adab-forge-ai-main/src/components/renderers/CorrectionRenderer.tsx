import { X, Check } from "lucide-react";

interface Pair {
  wrong?: string;
  right?: string;
  rule?: string;
}

function parse(content: string): Pair[] {
  try {
    const j = JSON.parse(content);
    if (Array.isArray(j)) return j;
  } catch {}
  // fallback: blocks separated by ---
  return content.split(/\n---\n|\n\n+/).map((b) => {
    const wrong = b.match(/(?:غلط|wrong)[:：]\s*(.+)/i)?.[1];
    const right = b.match(/(?:درست|right|correct)[:：]\s*(.+)/i)?.[1];
    const rule = b.match(/(?:قاعدہ|rule)[:：]\s*(.+)/i)?.[1];
    return { wrong, right, rule };
  }).filter((p) => p.wrong || p.right);
}

export function CorrectionRenderer({ content }: { content: string }) {
  const items = parse(content);
  if (!items.length) return <p className="urdu text-foreground">{content}</p>;

  return (
    <div className="space-y-4">
      {items.map((p, i) => (
        <div key={i} className="overflow-hidden rounded-xl border border-border bg-card">
          {p.wrong && (
            <div className="flex items-start gap-3 border-b border-border bg-destructive/5 p-4">
              <X className="mt-1 h-4 w-4 shrink-0 text-destructive" />
              <p className="urdu flex-1 text-foreground line-through decoration-destructive/60">{p.wrong}</p>
            </div>
          )}
          {p.right && (
            <div className="flex items-start gap-3 bg-primary/5 p-4">
              <Check className="mt-1 h-4 w-4 shrink-0 text-primary" />
              <p className="urdu flex-1 font-medium text-primary">{p.right}</p>
            </div>
          )}
          {p.rule && (
            <div className="border-t border-border bg-muted/40 px-4 py-2">
              <span className="text-xs uppercase tracking-wider text-[var(--gold)]">Rule</span>
              <p className="urdu text-sm text-muted-foreground">{p.rule}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
