export type Mode = "tutor" | "paper";

export type Genre =
  | "mcq"
  | "word_meanings"
  | "tashreeh"
  | "nasar_tashreeh"
  | "sentence_correction"
  | "letter"
  | "application"
  | "dialogue"
  | "story"
  | "paper_generation"
  | "khulasa"
  | "markazi_khyal"
  | "translation"
  | "qa"
  | "vocabulary"
  | "idioms_proverbs"
  | "grammar"
  | "zarbul_imsal"
  | "comprehension"
  | "translation"
  | "summary_detailed"
  | "default";

export interface Message {
  id: string;
  role: "user" | "assistant";
  mode: Mode;
  genre: Genre;
  content: string;
  metadata?: Record<string, unknown>;
  streaming?: boolean;
  createdAt: number;
}

export interface Conversation {
  id: string;
  title: string;
  mode: Mode;
  messages: Message[];
  createdAt: number;
}

export interface QueryPayload {
  query: string;
  mode: Mode;
  genre?: Genre;
  dataset: string;
  stream: boolean;
  class?: string;
  questions?: string[];
  top_k?: number;
  hybrid?: boolean;
  bm25_weight?: number;
}
