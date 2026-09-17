import { AURORA_API_BASE_URL } from "@/config/api";
import { Message, RuntimeFile, SubjectContext } from "@/types";


export interface StreamChatParams {
  messages: Message[];
  subject: SubjectContext;
  model: string;
  signal: AbortSignal;
  onChunk: (chunk: string) => void;
  onComplete: (fullText: string) => void;
  onError: (error: Error) => void;
}

export async function streamChatCompletion({
  messages,
  subject,
  model,
  signal,
  onChunk,
  onComplete,
  onError,
}: StreamChatParams): Promise<void> {
  try {
    const formattedMessages = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const response = await fetch(`${AURORA_API_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: formattedMessages,
        stream: true,
        extra_body: {
          subject_context: subject,
        },
      }),
      signal,
    }).catch((err) => {
      // Catch connection errors (e.g. backend server offline)
      if (err.name === "AbortError") {
        throw err;
      }
      return null;
    });

    if (!response || !response.ok || !response.body) {
      // Fallback demonstration streaming engine for local standalone execution
      await simulateEducationalResponse({
        messages,
        subject,
        model,
        signal,
        onChunk,
        onComplete,
      });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let accumulatedText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last incomplete fragment in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue;

        if (trimmedLine.startsWith("data: ")) {
          const dataStr = trimmedLine.replace(/^data:\s*/, "").trim();
          if (dataStr === "[DONE]") continue;

          try {
            const parsed = JSON.parse(dataStr);
            const delta = parsed.choices?.[0]?.delta?.content || "";
            if (delta) {
              accumulatedText += delta;
              onChunk(delta);
            }
          } catch {
            // Only forward as raw text if it does not look like an incomplete JSON object
            if (!dataStr.startsWith("{") && !dataStr.startsWith("[")) {
              accumulatedText += dataStr;
              onChunk(dataStr);
            }
          }
        }
      }
    }

    // Flush any remaining buffer if it contains a completed SSE event
    if (buffer.trim()) {
      const trimmedLine = buffer.trim();
      if (trimmedLine.startsWith("data: ")) {
        const dataStr = trimmedLine.replace(/^data:\s*/, "").trim();
        if (dataStr !== "[DONE]") {
          try {
            const parsed = JSON.parse(dataStr);
            const delta = parsed.choices?.[0]?.delta?.content || "";
            if (delta) {
              accumulatedText += delta;
              onChunk(delta);
            }
          } catch {
            if (!dataStr.startsWith("{") && !dataStr.startsWith("[")) {
              accumulatedText += dataStr;
              onChunk(dataStr);
            }
          }
        }
      }
    }

    onComplete(accumulatedText);
  } catch (error: any) {
    if (error.name === "AbortError") {
      // Clean handle for user requested abort
      return;
    }
    onError(error instanceof Error ? error : new Error(String(error)));
  }
}

// Fallback Educational Intelligence Stream Simulator
async function simulateEducationalResponse({
  messages,
  subject,
  model,
  signal,
  onChunk,
  onComplete,
}: Omit<StreamChatParams, "onError">): Promise<void> {
  const lastUserMessage = messages[messages.length - 1]?.content || "";
  const detectedSubject = subject === "AUTO" ? autoDetectSubject(lastUserMessage) : subject;

  const mockResponse = generateDomainKnowledgeResponse(lastUserMessage, detectedSubject, model);
  let accumulated = "";

  const words = mockResponse.split(" ");
  for (let i = 0; i < words.length; i++) {
    if (signal.aborted) {
      throw new DOMException("Aborted by user", "AbortError");
    }

    const word = (i === 0 ? "" : " ") + words[i];
    accumulated += word;
    onChunk(word);

    // Variable latency per token stream simulation
    await new Promise((res) => setTimeout(res, 25 + Math.random() * 20));
  }

  onComplete(accumulated);
}

function autoDetectSubject(prompt: string): SubjectContext | "OUT_OF_DOMAIN" {
  const lower = prompt.toLowerCase();
  if (lower.includes("sql") || lower.includes("table") || lower.includes("join") || lower.includes("index") || lower.includes("db") || lower.includes("database") || lower.includes("acid") || lower.includes("relational") || lower.includes("schema") || lower.includes("normalization")) {
    return "DBMS";
  }
  if (lower.includes("data structure") || lower.includes("datastructure") || lower.includes("data") || lower.includes("tree") || lower.includes("graph") || lower.includes("array") || lower.includes("sort") || lower.includes("complexity") || lower.includes("linked list") || lower.includes("heap") || lower.includes("stack") || lower.includes("queue") || lower.includes("recursion") || lower.includes("algo") || lower.includes("search") || lower.includes("hash") || lower.includes("binary")) {
    return "DSA";
  }
  if (lower.includes("class") || lower.includes("object") || lower.includes("polymorphism") || lower.includes("inheritance") || lower.includes("encapsulation") || lower.includes("solid") || lower.includes("oop") || lower.includes("method")) {
    return "OOPS";
  }
  if (lower.includes("process") || lower.includes("thread") || lower.includes("deadlock") || lower.includes("memory") || lower.includes("semaphore") || lower.includes("page fault") || lower.includes("kernel") || lower.includes("cpu") || lower.includes("scheduling") || lower.includes("operating system") || lower.includes("mutex")) {
    return "OS";
  }
  if (lower.includes("tcp") || lower.includes("ip") || lower.includes("osi") || lower.includes("packet") || lower.includes("socket") || lower.includes("router") || lower.includes("http") || lower.includes("dns") || lower.includes("protocol") || lower.includes("network") || lower.includes("bandwidth") || lower.includes("lan") || lower.includes("wan")) {
    return "CNT";
  }
  if (lower.includes("uml") || lower.includes("agile") || lower.includes("waterfall") || lower.includes("requirements") || lower.includes("design pattern") || lower.includes("testing") || lower.includes("software engineering") || lower.includes("sdlc") || lower.includes("scrum")) {
    return "OOSE";
  }

  // Generic CS query check
  if (lower.includes("code") || lower.includes("program") || lower.includes("computer") || lower.includes("developer") || lower.includes("function") || lower.includes("variable") || lower.includes("algorithm")) {
    return "DSA";
  }

  return "OUT_OF_DOMAIN";
}

function generateDomainKnowledgeResponse(prompt: string, subject: SubjectContext | "OUT_OF_DOMAIN", model: string): string {
  if (subject === "OUT_OF_DOMAIN") {
    return "I am specialized exclusively in Computer Science curriculum domains (Database Management Systems, Data Structures & Algorithms, Object-Oriented Programming, Operating Systems, Computer Networks, and Software Engineering). This query does not fall within our supported educational subjects.";
  }

  const subjectPrefix = `[Aurora Domain Engine: ${subject} | Model: ${model}]`;

  if (subject === "DBMS") {
    return `${subjectPrefix}

### Relational Database Normalization & ACID Properties

In Database Management Systems, ensuring data consistency and minimal redundancy requires adhering to **Normal Forms** and **ACID Guarantees**.

#### 1. ACID Properties
- **Atomicity**: All transactions execute completely or roll back entirely.
- **Consistency**: Database transitions from one valid state to another.
- **Isolation**: Concurrent transactions execute independently (\`READ COMMITTED\`, \`REPEATABLE READ\`, \`SERIALIZABLE\`).
- **Durability**: Committed changes persist even in hardware crashes.

#### 2. Standard Query Example
\`\`\`sql
-- SQL Query demonstrating B-Tree Index utilization
SELECT e.id, e.name, d.department_name
FROM employees e
JOIN departments d ON e.dept_id = d.id
WHERE e.salary > 75000
ORDER BY e.hire_date DESC;
\`\`\`

#### Mathematical Formulation for Relational Select:
$$\\sigma_{C}(R) = \\{ t \\in R \\mid C(t) = \\text{true} \\}$$

How would you like to explore transaction isolation levels or indexing strategies next?`;
  }

  if (subject === "DSA") {
    return `${subjectPrefix}

### Algorithm Analysis & Binary Search Tree (BST) Properties

When solving problems in **Data Structures & Algorithms**, analyzing time and space complexity using Asymptotic Notation is essential.

#### Time Complexity Comparison

| Algorithm | Average Time | Worst Time | Space Complexity |
| :--- | :--- | :--- | :--- |
| **QuickSort** | $\\mathcal{O}(n \\log n)$ | $\\mathcal{O}(n^2)$ | $\\mathcal{O}(\\log n)$ |
| **MergeSort** | $\\mathcal{O}(n \\log n)$ | $\\mathcal{O}(n \\log n)$ | $\\mathcal{O}(n)$ |
| **Binary Search** | $\\mathcal{O}(\\log n)$ | $\\mathcal{O}(\\log n)$ | $\\mathcal{O}(1)$ |

#### Python Tree Node Implementation
\`\`\`python
class TreeNode:
    def __init__(self, val: int = 0):
        self.val = val
        self.left: TreeNode | None = None
        self.right: TreeNode | None = None

def insert_into_bst(root: TreeNode | None, val: int) -> TreeNode:
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert_into_bst(root.left, val)
    else:
        root.right = insert_into_bst(root.right, val)
    return root
\`\`\`

Would you like to analyze dynamic programming optimal substructure or graph traversal algorithms?`;
  }

  return `${subjectPrefix}

### Core Educational Principles in ${subject}

Aurora Engine processed your request under the **${subject}** context.

Key conceptual pillars:
1. **Core Abstraction**: Clean separation of interface definitions from underlying domain implementation.
2. **System Architecture**: High cohesion, loose coupling, and strict modularity.
3. **Verification**: Automated validation and empirical benchmarking.

\`\`\`typescript
// Code snippet representing modular architecture
export interface DomainService<T> {
  execute(input: T): Promise<DomainResult>;
}
\`\`\`

Mathematical relationship for system performance:
$$T_{\\text{total}} = T_{\\text{ingestion}} + T_{\\text{inference}} + \\epsilon$$

Feel free to ask follow-up questions on this topic!`;
}

export async function transcribeAudioBlob(audioBlob: Blob): Promise<{ text: string }> {
  try {
    const formData = new FormData();
    const mimeType = audioBlob.type || "audio/webm";
    const ext = mimeType.includes("webm")
      ? ".webm"
      : mimeType.includes("ogg")
      ? ".ogg"
      : mimeType.includes("mp4") || mimeType.includes("m4a")
      ? ".m4a"
      : ".wav";

    formData.append("file", audioBlob, `speech_recording${ext}`);

    const response = await fetch(`${AURORA_API_BASE_URL}/speech/transcribe`, {
      method: "POST",
      body: formData,
    }).catch(() => null);

    if (!response || !response.ok) {
      // Secondary endpoint attempt for LAN / fallback routes
      const altUrl = AURORA_API_BASE_URL.endsWith("/v1")
        ? AURORA_API_BASE_URL.replace(/\/v1$/, "") + "/api/speech/transcribe"
        : `${AURORA_API_BASE_URL}/api/speech/transcribe`;

      const altResponse = await fetch(altUrl, {
        method: "POST",
        body: formData,
      }).catch(() => null);

      if (altResponse && altResponse.ok) {
        return await altResponse.json();
      }
      throw new Error("STT server endpoint unavailable");
    }

    return await response.json();
  } catch (error: any) {
    console.warn("Speech transcription request failed:", error);
    throw error;
  }
}

export async function uploadFile(
  file: File,
  conversationId: string
): Promise<RuntimeFile> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("conversation_id", conversationId);

  // Note: Do NOT set Content-Type header; browser must set multipart boundary automatically.
  const response = await fetch(`${AURORA_API_BASE_URL}/files/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = `Upload failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  return (await response.json()) as RuntimeFile;
}

export async function getFileMetadata(
  fileId: string,
  conversationId?: string
): Promise<RuntimeFile> {
  const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : "";
  const response = await fetch(`${AURORA_API_BASE_URL}/files/${encodeURIComponent(fileId)}${query}`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Failed to retrieve file metadata (${response.status})`);
  }

  return (await response.json()) as RuntimeFile;
}

export async function deleteFile(
  fileId: string,
  conversationId?: string
): Promise<boolean> {
  const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : "";
  const response = await fetch(`${AURORA_API_BASE_URL}/files/${encodeURIComponent(fileId)}${query}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete file (${response.status})`);
  }

  const result = await response.json();
  return !!result.deleted;
}


