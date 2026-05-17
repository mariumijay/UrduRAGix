import type { QueryPayload } from "@/types/rag";

export const API_BASE = "http://localhost:8000";

/**
 * Streams /query from the FastAPI backend.
 * Yields incremental text chunks. Tries SSE-style `data: ` parsing first,
 * falls back to raw text streaming.
 */
export async function* streamQuery(
  payload: QueryPayload,
  signal?: AbortSignal,
): AsyncGenerator<{ chunk?: string; meta?: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok) throw new Error(`Backend ${res.status}: ${await res.text()}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE framing: split on double newline
    const frames = buffer.split(/\n\n/);
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.trim();
      if (!line) continue;
      if (line.startsWith("data:")) {
        const data = line.slice(5).trim();
        if (data === "[DONE]") return;
        try {
          const parsed = JSON.parse(data);
          if (parsed.chunk || parsed.content || parsed.delta) {
            yield { chunk: parsed.chunk ?? parsed.content ?? parsed.delta, meta: parsed.metadata };
          } else if (typeof parsed === "string") {
            yield { chunk: parsed };
          } else {
            yield { meta: parsed };
          }
        } catch {
          yield { chunk: data };
        }
      } else {
        // raw text streaming
        yield { chunk: line };
      }
    }
  }
  if (buffer.trim()) yield { chunk: buffer };
}
