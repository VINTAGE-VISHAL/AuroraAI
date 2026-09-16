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

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  subject?: SubjectContext;
  model?: string;
  timestamp: number;
  status?: "streaming" | "complete" | "cancelled" | "error";
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
