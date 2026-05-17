import { createFileRoute } from "@tanstack/react-router";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatPanel } from "@/components/chat/ChatPanel";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RAGix — Premium Urdu AI Suite" },
      {
        name: "description",
        content:
          "RAGix is a semantic Urdu intelligence suite — tutor mode and Punjab Board paper generation, powered by retrieval-augmented generation.",
      },
      { property: "og:title", content: "RAGix — Premium Urdu AI Suite" },
      {
        property: "og:description",
        content: "Tutor mode and Punjab Board paper generation, powered by RAG.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar />
      <ChatPanel />
    </div>
  );
}
