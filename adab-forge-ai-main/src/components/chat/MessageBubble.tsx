import { motion } from "framer-motion";
import type { Message } from "@/types/rag";
import { GenreRenderer } from "@/components/renderers";
import { User, Sparkles } from "lucide-react";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const isUrdu = /[\u0600-\u06FF]/.test(message.content);

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end gap-3"
      >
        <div className="max-w-2xl rounded-2xl rounded-tr-sm bg-[var(--gradient-emerald)] px-5 py-3 text-primary-foreground shadow-[var(--shadow-emerald)]">
          <p className={`${isUrdu ? "urdu text-lg" : "text-sm"} whitespace-pre-wrap`}>
            {message.content}
          </p>
        </div>
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--gradient-emerald)] shadow-[var(--shadow-gold)]">
        <Sparkles className="h-4 w-4 text-[var(--gold)]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex items-center gap-2 text-xs">
          <span className="font-semibold text-primary">RAGix</span>
          <span className="rounded-full bg-[var(--gold)]/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[var(--gold)]">
            {message.genre}
          </span>
        </div>
        <GenreRenderer
          genre={message.genre}
          content={message.content}
          streaming={message.streaming}
        />
      </div>
    </motion.div>
  );
}
