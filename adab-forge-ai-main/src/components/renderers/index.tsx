import type { Genre } from "@/types/rag";
import { MCQRenderer } from "./MCQRenderer";
import { TashreehRenderer } from "./TashreehRenderer";
import { LetterRenderer } from "./LetterRenderer";
import { CorrectionRenderer } from "./CorrectionRenderer";
import { ExamPaperRenderer } from "./ExamPaperRenderer";
import { DefaultRenderer } from "./DefaultRenderer";

export function GenreRenderer({
  genre,
  content,
  streaming,
}: {
  genre: Genre;
  content: string;
  streaming?: boolean;
}) {
  switch (genre) {
    case "mcq":
      return <MCQRenderer content={content} />;
    case "tashreeh":
      return <TashreehRenderer content={content} />;
    case "letter":
    case "story":
      return <LetterRenderer content={content} />;
    case "sentence_correction":
      return <CorrectionRenderer content={content} />;
    case "paper_generation":
      return <ExamPaperRenderer content={content} streaming={streaming} />;
    default:
      return <DefaultRenderer content={content} streaming={streaming} />;
  }
}
