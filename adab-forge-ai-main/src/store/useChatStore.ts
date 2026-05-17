import { create } from "zustand";
import type { Conversation, Genre, Message, Mode } from "@/types/rag";

interface ExamSettings {
  class: string;
  questions: string[];
}

interface RetrievalSettings {
  topK: number;
  hybrid: boolean;
  bm25Weight: number;
}

interface TutorSettings {
  dataset: string;
  responseStyle: "concise" | "detailed";
  streaming: boolean;
}

interface ChatState {
  mode: Mode;
  conversations: Conversation[];
  activeId: string | null;
  tutor: TutorSettings;
  exam: ExamSettings;
  retrieval: RetrievalSettings;

  setMode: (m: Mode) => void;
  newConversation: () => string;
  setActive: (id: string) => void;
  deleteConversation: (id: string) => void;
  addMessage: (msg: Message) => void;
  appendToMessage: (id: string, chunk: string) => void;
  setMessageMeta: (id: string, patch: Partial<Message>) => void;

  setTutor: (p: Partial<TutorSettings>) => void;
  setExam: (p: Partial<ExamSettings>) => void;
  setRetrieval: (p: Partial<RetrievalSettings>) => void;
}

const seedId = () => Math.random().toString(36).slice(2, 11);

export const useChatStore = create<ChatState>((set, get) => ({
  mode: "tutor",
  conversations: [],
  activeId: null,

  tutor: { dataset: "urdu_a", responseStyle: "detailed", streaming: true },
  exam: { class: "10th", questions: ["Q2", "Q3", "Q4"] },
  retrieval: { topK: 5, hybrid: true, bm25Weight: 0.4 },

  setMode: (mode) => set({ mode }),

  newConversation: () => {
    const id = seedId();
    const conv: Conversation = {
      id,
      title: get().mode === "tutor" ? "نئی گفتگو" : "نیا پرچہ",
      mode: get().mode,
      messages: [],
      createdAt: Date.now(),
    };
    set((s) => ({ conversations: [conv, ...s.conversations], activeId: id }));
    return id;
  },

  setActive: (id) => set({ activeId: id }),

  deleteConversation: (id) =>
    set((s) => {
      const conversations = s.conversations.filter((c) => c.id !== id);
      return {
        conversations,
        activeId: s.activeId === id ? conversations[0]?.id ?? null : s.activeId,
      };
    }),

  addMessage: (msg) =>
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.id === s.activeId
          ? {
              ...c,
              title:
                c.messages.length === 0 && msg.role === "user"
                  ? msg.content.slice(0, 40)
                  : c.title,
              messages: [...c.messages, msg],
            }
          : c,
      ),
    })),

  appendToMessage: (id, chunk) =>
    set((s) => ({
      conversations: s.conversations.map((c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.id === id ? { ...m, content: m.content + chunk } : m,
        ),
      })),
    })),

  setMessageMeta: (id, patch) =>
    set((s) => ({
      conversations: s.conversations.map((c) => ({
        ...c,
        messages: c.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
      })),
    })),

  setTutor: (p) => set((s) => ({ tutor: { ...s.tutor, ...p } })),
  setExam: (p) => set((s) => ({ exam: { ...s.exam, ...p } })),
  setRetrieval: (p) => set((s) => ({ retrieval: { ...s.retrieval, ...p } })),
}));

export const newMessageId = () => Math.random().toString(36).slice(2, 11);
