import { useChatStore } from "@/store/useChatStore";
import { motion } from "framer-motion";
import {
  GraduationCap,
  FileText,
  Plus,
  Trash2,
  Settings2,
  Database,
  Sliders,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";

export function Sidebar() {
  const {
    mode,
    setMode,
    conversations,
    activeId,
    setActive,
    newConversation,
    deleteConversation,
    tutor,
    setTutor,
    exam,
    setExam,
    retrieval,
    setRetrieval,
  } = useChatStore();

  const [openSection, setOpenSection] = useState<string | null>("settings");

  const toggle = (k: string) => setOpenSection((s) => (s === k ? null : k));

  return (
    <aside className="flex h-screen w-80 shrink-0 flex-col border-r border-border bg-card/60 backdrop-blur-xl">
      {/* Brand */}
      <div className="relative overflow-hidden border-b border-border p-5">
        <div className="geo-pattern absolute inset-0 opacity-50" />
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--gradient-emerald)] shadow-[var(--shadow-gold)]">
              <span className="arabic text-xl font-bold text-[var(--gold)]">ر</span>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-primary">
                RAG<span className="shimmer-gold">ix</span>
              </h1>
              <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Urdu AI Suite
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mode switcher */}
      <div className="p-4">
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-muted p-1">
          <button
            onClick={() => setMode("tutor")}
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${
              mode === "tutor"
                ? "bg-[var(--gradient-emerald)] text-primary-foreground shadow-[var(--shadow-emerald)]"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <GraduationCap className="h-3.5 w-3.5" />
            Tutor
          </button>
          <button
            onClick={() => setMode("paper")}
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${
              mode === "paper"
                ? "bg-[var(--gradient-emerald)] text-primary-foreground shadow-[var(--shadow-emerald)]"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            Paper
          </button>
        </div>

        <button
          onClick={() => newConversation()}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--gold)]/40 bg-[var(--gold)]/10 px-3 py-2 text-sm font-medium text-primary transition hover:bg-[var(--gold)]/20"
        >
          <Plus className="h-4 w-4" />
          New conversation
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-3">
        <div className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          History
        </div>
        {conversations.length === 0 && (
          <div className="urdu px-2 py-4 text-center text-sm text-muted-foreground">
            ابھی کوئی گفتگو نہیں
          </div>
        )}
        <div className="space-y-1">
          {conversations.map((c) => (
            <motion.div
              key={c.id}
              layout
              className={`group flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                activeId === c.id
                  ? "bg-primary/10 text-primary"
                  : "text-foreground hover:bg-muted"
              }`}
            >
              <button onClick={() => setActive(c.id)} className="urdu flex-1 truncate text-right">
                {c.title}
              </button>
              <button
                onClick={() => deleteConversation(c.id)}
                className="opacity-0 transition group-hover:opacity-100"
              >
                <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
              </button>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Settings */}
      <div className="border-t border-border p-3">
        <SectionHeader
          icon={<Settings2 className="h-3.5 w-3.5" />}
          label={mode === "tutor" ? "Tutor settings" : "Exam settings"}
          open={openSection === "settings"}
          onToggle={() => toggle("settings")}
        />
        {openSection === "settings" && (
          <div className="mt-2 space-y-3 px-1 pb-3">
            {mode === "tutor" ? (
              <>
                <Field label="Dataset">
                  <Select
                    value={tutor.dataset}
                    onChange={(v) => setTutor({ dataset: v })}
                    options={[
                      ["urdu_a", "Urdu A"],
                      ["urdu_b", "Urdu B"],
                      ["islamiat", "Islamiat"],
                    ]}
                  />
                </Field>
                <Field label="Response style">
                  <Select
                    value={tutor.responseStyle}
                    onChange={(v) => setTutor({ responseStyle: v as "concise" | "detailed" })}
                    options={[
                      ["concise", "Concise"],
                      ["detailed", "Detailed"],
                    ]}
                  />
                </Field>
                <Toggle
                  label="Streaming"
                  checked={tutor.streaming}
                  onChange={(v) => setTutor({ streaming: v })}
                />
              </>
            ) : (
              <>
                <Field label="Class">
                  <Select
                    value={exam.class}
                    onChange={(v) => setExam({ class: v })}
                    options={[
                      ["9th", "9th"],
                      ["10th", "10th"],
                      ["11th", "11th"],
                      ["12th", "12th"],
                    ]}
                  />
                </Field>
                <Field label="Questions">
                  <div className="flex flex-wrap gap-1.5">
                    {["Q1", "Q2", "Q3", "Q4", "Q5"].map((q) => {
                      const on = exam.questions.includes(q);
                      return (
                        <button
                          key={q}
                          onClick={() =>
                            setExam({
                              questions: on
                                ? exam.questions.filter((x) => x !== q)
                                : [...exam.questions, q],
                            })
                          }
                          className={`rounded-md border px-2 py-1 text-xs transition ${
                            on
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-border bg-card text-muted-foreground hover:border-primary"
                          }`}
                        >
                          {q}
                        </button>
                      );
                    })}
                  </div>
                </Field>
              </>
            )}
          </div>
        )}

        <SectionHeader
          icon={<Database className="h-3.5 w-3.5" />}
          label="Retrieval"
          open={openSection === "retrieval"}
          onToggle={() => toggle("retrieval")}
        />
        {openSection === "retrieval" && (
          <div className="mt-2 space-y-3 px-1 pb-3">
            <Field label={`Top K: ${retrieval.topK}`}>
              <input
                type="range"
                min={1}
                max={20}
                value={retrieval.topK}
                onChange={(e) => setRetrieval({ topK: Number(e.target.value) })}
                className="w-full accent-[var(--emerald)]"
              />
            </Field>
            <Toggle
              label="Hybrid search"
              checked={retrieval.hybrid}
              onChange={(v) => setRetrieval({ hybrid: v })}
            />
            <Field label={`BM25 weight: ${retrieval.bm25Weight.toFixed(2)}`}>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={retrieval.bm25Weight}
                onChange={(e) => setRetrieval({ bm25Weight: Number(e.target.value) })}
                className="w-full accent-[var(--gold)]"
              />
            </Field>
          </div>
        )}
      </div>

      <div className="border-t border-border p-3 text-center text-[10px] text-muted-foreground">
        <Sliders className="mx-auto mb-1 h-3 w-3" />
        Connected to <span className="text-primary">localhost:8000</span>
      </div>
    </aside>
  );
}

function SectionHeader({
  icon,
  label,
  open,
  onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition hover:text-foreground"
    >
      <span className="flex items-center gap-2">
        {icon}
        {label}
      </span>
      <ChevronDown className={`h-3.5 w-3.5 transition ${open ? "rotate-180" : ""}`} />
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border border-border bg-card px-2 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
    >
      {options.map(([v, l]) => (
        <option key={v} value={v}>
          {l}
        </option>
      ))}
    </select>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-muted-foreground">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition ${
          checked ? "bg-[var(--gradient-emerald)]" : "bg-muted"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-card shadow transition ${
            checked ? "left-[18px]" : "left-0.5"
          }`}
        />
      </button>
    </div>
  );
}
