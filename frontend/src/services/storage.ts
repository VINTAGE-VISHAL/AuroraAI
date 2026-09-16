import { Conversation, Project, StorageAdapter } from "@/types";

const STORAGE_KEY_CONVS = "aurora_conversations_v1";
const STORAGE_KEY_PROJECTS = "samarthan_projects_v1";

export class LocalStorageAdapter implements StorageAdapter {
  private isAvailable(): boolean {
    return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
  }

  getConversations(): Conversation[] {
    if (!this.isAvailable()) return [];
    try {
      const data = localStorage.getItem(STORAGE_KEY_CONVS);
      if (!data) return [];
      const parsed = JSON.parse(data) as Conversation[];
      return Array.isArray(parsed) ? parsed.sort((a, b) => b.updatedAt - a.updatedAt) : [];
    } catch (e) {
      console.error("Failed to read conversations from localStorage:", e);
      return [];
    }
  }

  getConversation(id: string): Conversation | null {
    const conversations = this.getConversations();
    return conversations.find((c) => c.id === id) || null;
  }

  saveConversation(conversation: Conversation): void {
    if (!this.isAvailable()) return;
    try {
      const conversations = this.getConversations();
      const index = conversations.findIndex((c) => c.id === conversation.id);
      const updatedConversation = {
        ...conversation,
        updatedAt: Date.now(),
      };

      if (index >= 0) {
        conversations[index] = updatedConversation;
      } else {
        conversations.unshift(updatedConversation);
      }

      localStorage.setItem(STORAGE_KEY_CONVS, JSON.stringify(conversations));
    } catch (e) {
      console.error("Failed to save conversation to localStorage:", e);
    }
  }

  deleteConversation(id: string): void {
    if (!this.isAvailable()) return;
    try {
      const conversations = this.getConversations().filter((c) => c.id !== id);
      localStorage.setItem(STORAGE_KEY_CONVS, JSON.stringify(conversations));
    } catch (e) {
      console.error("Failed to delete conversation from localStorage:", e);
    }
  }

  clearConversations(): void {
    if (!this.isAvailable()) return;
    try {
      localStorage.removeItem(STORAGE_KEY_CONVS);
    } catch (e) {
      console.error("Failed to clear conversations from localStorage:", e);
    }
  }

  getProjects(): Project[] {
    if (!this.isAvailable()) return [];
    try {
      const data = localStorage.getItem(STORAGE_KEY_PROJECTS);
      if (!data) return [];
      const parsed = JSON.parse(data) as Project[];
      return Array.isArray(parsed) ? parsed.sort((a, b) => b.updatedAt - a.updatedAt) : [];
    } catch (e) {
      console.error("Failed to read projects from localStorage:", e);
      return [];
    }
  }

  saveProject(project: Project): void {
    if (!this.isAvailable()) return;
    try {
      const projects = this.getProjects();
      const index = projects.findIndex((p) => p.id === project.id);
      const updatedProject = {
        ...project,
        updatedAt: Date.now(),
      };

      if (index >= 0) {
        projects[index] = updatedProject;
      } else {
        projects.unshift(updatedProject);
      }

      localStorage.setItem(STORAGE_KEY_PROJECTS, JSON.stringify(projects));
    } catch (e) {
      console.error("Failed to save project to localStorage:", e);
    }
  }

  deleteProject(id: string): void {
    if (!this.isAvailable()) return;
    try {
      const projects = this.getProjects().filter((p) => p.id !== id);
      localStorage.setItem(STORAGE_KEY_PROJECTS, JSON.stringify(projects));

      // Remove projectId assignment from associated conversations
      const conversations = this.getConversations();
      let modified = false;
      const updatedConvs = conversations.map((c) => {
        if (c.projectId === id) {
          modified = true;
          return { ...c, projectId: undefined };
        }
        return c;
      });
      if (modified) {
        localStorage.setItem(STORAGE_KEY_CONVS, JSON.stringify(updatedConvs));
      }
    } catch (e) {
      console.error("Failed to delete project from localStorage:", e);
    }
  }
}

export const storageAdapter = new LocalStorageAdapter();
