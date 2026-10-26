export type SubjectContext =
  | "AUTO"
  | "DBMS"
  | "DSA"
  | "OOPS"
  | "OS"
  | "CNT"
  | "OOSE";

export interface ModelOption {
  id: string;
  name: string;
  description: string;
  domain?: SubjectContext;
  isDefault?: boolean;
}

export interface MessageAttachment {
  fileId: string;
  filename: string;
  sizeBytes?: number;
  fileType?: string;
  status: "indexing" | "ready" | "failed";
  usedDocumentContext?: boolean;
}

export interface Citation {
  chunk_id: string;
  file_id: string;
  filename: string;
  source_page?: number | null;
  chunk_index: number;
  relevance_score?: number;
  label: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  subject?: SubjectContext;
  model?: string;
  timestamp: number;
  status?: "streaming" | "complete" | "cancelled" | "error";
  attachment?: MessageAttachment;
  citations?: Citation[];
  metadata?: {
    confidenceScore?: number;
    sourcesCount?: number;
    tokensPerSecond?: number;
  };
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  createdAt: number;
  updatedAt: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  activeSubject: SubjectContext;
  activeModel: string;
  pinned?: boolean;
  projectId?: string;
  createdAt: number;
  updatedAt: number;
}

export interface StorageAdapter {
  getConversations(): Conversation[];
  getConversation(id: string): Conversation | null;
  saveConversation(conversation: Conversation): void;
  deleteConversation(id: string): void;
  clearConversations(): void;
  getProjects(): Project[];
  saveProject(project: Project): void;
  deleteProject(id: string): void;
}

export interface RuntimeFile {
  file_id: string;
  conversation_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  extension: string;
  status: "uploading" | "stored" | "processing" | "ready" | "failed" | "deleted";
  created_at: number;
}

export interface IndexingResponse {
  file_id: string;
  conversation_id: string;
  indexed_count: number;
  dimension: number;
  chunks: Array<{
    chunk_id: string;
    file_id: string;
    filename: string;
    chunk_index: number;
    source_page?: number | null;
    char_count: number;
  }>;
  success: boolean;
}


