import { useEffect, useRef, useState } from "react";
import { useChatStore, newMessageId } from "@/store/useChatStore";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { streamQuery } from "@/services/api";
import type { Genre, Message } from "@/types/rag";
import { Sparkles } from "lucide-react";

function detectGenre(text: string): Genre {
  const t = text.toLowerCase();
  // MCQ / Objective
  if (/mcq|سوال نمبر|چار میں سے|multiple choice|objective/.test(text)) {
    return "mcq";
  }

  // Paper Generation
  if (/پرچہ|paper|exam|پیپر|test paper/.test(text)) {
    return "paper_generation";
  }

  // Summary
  if (/خلاصہ|summary|khulasa/.test(text)) {
    return "khulasa";
  }

  // Markazi Khyal / Moral
  if (/مرکزی خیال|مرکزی خيال|markazi\s*khyal|moral|theme/.test(text)) {
    return "markazi_khyal";
  }

  // Tashreeh (Poetry / Explanation)
  if (/تشریح|tashreeh|شعر|ghazal|nazm|نظم|غزل|poem|poetry|explain/.test(text)) {
    return "tashreeh";
  }

  // Letter Writing
  if (/خط|letter|personal letter|friendly letter|formal letter/.test(text)) {
    return "letter";
  }

  // Application Writing
  if (/درخواست|application|job application|leave application|request application/.test(text)) {
    return "application";
  }
  // Story Writing
  if (/کہانی|story|short story|write a story/.test(text)) {
    return "story";
  }
  // Dialogue Writing
  if (/مکالمہ|dialogue|conversation|write a dialogue|complete dialogue/.test(text)) {
    return "dialogue";
  }

  // Sentence Correction
  if (/درست|غلط|اصلاح|correct|sentence correction|grammar/.test(text)) {
    return "sentence_correction";
  }

  // Translation (very useful for Urdu RAG systems)
  if (/ترجمہ|translate|translation/.test(text)) {
    return "translation";
  }

  // Question Answer / Long Question
  if (/سوال جواب|short question|explain question|answer the question/.test(text)) {
    return "qa";
  }

  // Vocabulary / Meanings
  if (/معنی|لفظ|meaning|vocabulary|synonym|antonym/.test(text)) {
    return "vocabulary";
  }
  // Nasar Tashreeh (Prose Explanation)
  if (/(نثر|nasar|نثر تشریح|nasar tashreeh|prose explanation|explain passage)/i.test(text)) {
    return "nasar_tashreeh";
  }
  // Zarbul Imal (Proverbs)
  if (/(ضرب الامثال|zarbul imsal|proverb|proverbs|کہاوت)/i.test(text)) {
    return "zarbul_imsal";
  }
  // Sentence Correction / Grammar
  if (/(درست|غلط|اصلاح|sentence correction|grammar|correct sentence|صحیح جملہ)/i.test(text)) {
    return "sentence_correction";
  }
  // Vocabulary / Word Meanings
  if (/معنی|لفظ|meaning|vocabulary|word meaning|word_meanings|متضاد|مترادف/i.test(text)) {
    return "word_meanings";
  }
  // Comprehension / Reading Comprehension
  if (/comprehension|پیراگراف| lecture|سوالات پیراگراف|passage comprehension/i.test(text)) {
    return "comprehension";
  }

  return "default";
}

export function ChatPanel() {
  const {
    mode,
    conversations,
    activeId,
    newConversation,
    addMessage,
    appendToMessage,
    setMessageMeta,
    tutor,
    exam,
    retrieval,
  } = useChatStore();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const active = conversations.find((c) => c.id === activeId);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [active?.messages.length, active?.messages.at(-1)?.content.length]);

  const handleSend = async (text: string) => {
    setError(null);
    let convId = activeId;
    if (!convId) convId = newConversation();

    const genre: Genre = mode === "paper" ? "paper_generation" : detectGenre(text);

    const userMsg: Message = {
      id: newMessageId(),
      role: "user",
      mode,
      genre,
      content: text,
      createdAt: Date.now(),
    };
    addMessage(userMsg);

    const aiId = newMessageId();
    const aiMsg: Message = {
      id: aiId,
      role: "assistant",
      mode,
      genre,
      content: "",
      streaming: true,
      createdAt: Date.now(),
    };
    addMessage(aiMsg);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setBusy(true);

    try {
      for await (const part of streamQuery(
        {
          query: text,
          mode,
          genre,
          dataset: mode === "tutor" ? tutor.dataset : `class_${exam.class}`,
          stream: mode === "tutor" ? tutor.streaming : true,
          class: mode === "paper" ? exam.class : undefined,
          questions: mode === "paper" ? exam.questions : undefined,
          top_k: retrieval.topK,
          hybrid: retrieval.hybrid,
          bm25_weight: retrieval.bm25Weight,
        },
        ctrl.signal,
      )) {
        if (part.chunk) appendToMessage(aiId, part.chunk);
        if (part.meta?.genre) setMessageMeta(aiId, { genre: part.meta.genre as Genre });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg !== "AbortError" && !msg.includes("aborted")) {
        setError(msg);
        appendToMessage(aiId, `\n\n_⚠️ ${msg}_`);
      }
    } finally {
      setMessageMeta(aiId, { streaming: false });
      setBusy(false);
      abortRef.current = null;
    }
  };

  const handleStop = () => abortRef.current?.abort();

  return (
    <main className="flex h-screen flex-1 flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border bg-card/40 px-6 py-4 backdrop-blur-xl">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-primary">
            <Sparkles className="h-4 w-4 text-[var(--gold)]" />
            RAGix Assistant
          </h2>
          <p className="text-xs text-muted-foreground">Semantic Urdu Intelligence</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5">
          <span className={`h-2 w-2 rounded-full ${busy ? "bg-[var(--gold)] pulse-dot" : "bg-emerald-500"}`} />
          <span className="text-xs font-medium text-muted-foreground">
            {busy ? "Generating…" : "Online"}
          </span>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-8">
          {(!active || active.messages.length === 0) && <Welcome mode={mode} />}
          {active?.messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {error && active?.messages.length === 0 && (
            <p className="text-center text-sm text-destructive">{error}</p>
          )}
        </div>
      </div>

      {/* Input */}
      <ChatInput mode={mode} onSend={handleSend} onStop={handleStop} busy={busy} />
    </main>
  );
}

function Welcome({ mode }: { mode: "tutor" | "paper" }) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
      <div className="geo-pattern-gold relative mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-[var(--gradient-emerald)] shadow-[var(--shadow-emerald)]">
        <span className="arabic text-3xl font-bold text-[var(--gold)]">ر</span>
      </div>
      <h1 className="urdu text-3xl font-bold text-primary">
        {mode === "tutor" ? "اردو علم میں خوش آمدید" : "پرچہ ساز معاون"}
      </h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        {mode === "tutor"
          ? "Ask questions, request explanations, MCQs, letters, stories — in beautiful Urdu."
          : "Generate Punjab Board–style examination papers with authentic formatting."}
      </p>
    </div>
  );
}
