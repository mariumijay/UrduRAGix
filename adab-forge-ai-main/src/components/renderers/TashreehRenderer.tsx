import { motion } from "framer-motion";

export function TashreehRenderer({ content }: { content: string }) {
  // Parse loose structure: lines starting with markers
  const sections = content.split(/\n(?=##\s|---)/).map((s) => s.trim()).filter(Boolean);

  return (
    <div className="space-y-5">
      {sections.map((sec, i) => {
        const isVerse = /^##\s*(شعر|بیت|verse)/i.test(sec) || i === 0;
        const cleaned = sec.replace(/^##\s*[^\n]*\n?/, "").replace(/^---\s*/, "");
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            {isVerse ? (
              <div className="geo-pattern-gold relative overflow-hidden rounded-2xl border-2 border-[var(--gold)]/40 bg-card p-8 text-center">
                <div className="pointer-events-none absolute inset-0 bg-[var(--gradient-gold)] opacity-[0.04]" />
                <div className="relative">
                  <div className="mb-2 text-xs uppercase tracking-[0.3em] text-[var(--gold)]">Verse</div>
                  <p className="urdu text-2xl font-medium text-primary">{cleaned}</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-border bg-card p-6">
                <p className="urdu text-lg leading-loose text-foreground whitespace-pre-wrap">
                  {cleaned}
                </p>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
