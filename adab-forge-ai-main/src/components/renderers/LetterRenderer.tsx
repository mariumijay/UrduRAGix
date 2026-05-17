export function LetterRenderer({ content }: { content: string }) {
  return (
    <div className="exam-paper mx-auto max-w-2xl rounded-md">
      <div className="urdu text-lg leading-[39px] text-ink whitespace-pre-wrap">
        {content}
      </div>
    </div>
  );
}
