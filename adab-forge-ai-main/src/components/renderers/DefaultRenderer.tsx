import ReactMarkdown from "react-markdown";

export function DefaultRenderer({ content, streaming }: { content: string; streaming?: boolean }) {
  // Detect Urdu (RTL) content
  const isUrdu = /[\u0600-\u06FF]/.test(content);
  return (
    <div
      className={`prose prose-sm max-w-none text-foreground prose-headings:text-primary prose-strong:text-primary ${
        isUrdu ? "urdu text-lg" : ""
      } ${streaming ? "cursor-blink" : ""}`}
    >
      <ReactMarkdown>{content || (streaming ? "​" : "")}</ReactMarkdown>
    </div>
  );
}
