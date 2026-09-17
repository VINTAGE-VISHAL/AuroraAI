"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Conversation, Message, Project, SubjectContext } from "@/types";
import { storageAdapter } from "@/services/storage";
import { streamChatCompletion } from "@/services/api";
import { Sidebar } from "@/components/Sidebar";
import { ChatHeader } from "@/components/ChatHeader";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { AuroraOrb } from "@/components/AuroraOrb";
import { Sparkles, GraduationCap, Cpu, ShieldCheck, Folder, Plus, MessageSquare } from "lucide-react";

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeSubject, setActiveSubject] = useState<SubjectContext>("AUTO");
  const [activeModel, setActiveModel] = useState<string>("aurora-unified");
  const [isGenerating, setIsGenerating] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const activeAbortController = useRef<AbortController | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Responsive sidebar default: open on desktop (>=1024px), closed on mobile/tablet
  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth >= 1024) {
      setSidebarOpen(true);
    }
  }, []);

  // Hydrate conversations and projects from localStorage on initial mount
  useEffect(() => {
    const loadedConvs = storageAdapter.getConversations();
    const loadedProjs = storageAdapter.getProjects();
    setConversations(loadedConvs);
    setProjects(loadedProjs);

    if (loadedConvs.length > 0) {
      setActiveConversationId(loadedConvs[0].id);
      setActiveSubject(loadedConvs[0].activeSubject || "AUTO");
      setActiveModel(loadedConvs[0].activeModel || "aurora-unified");
    }
  }, []);

  const activeConversation = conversations.find((c) => c.id === activeConversationId) || null;
  const activeProject = projects.find((p) => p.id === activeProjectId) || null;

  // Auto scroll to bottom during streaming or message update
  const scrollToBottom = useCallback(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [activeConversation?.messages, scrollToBottom]);

  // Handle creating new conversation (optionally bound to a project)
  const handleNewConversation = useCallback((targetProjectId?: string) => {
    const projId = targetProjectId || activeProjectId || undefined;
    const newConv: Conversation = {
      id: `conv_${Date.now()}`,
      title: "New Session",
      messages: [],
      activeSubject: activeSubject,
      activeModel: activeModel,
      projectId: projId,
      pinned: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    storageAdapter.saveConversation(newConv);

    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, [activeSubject, activeModel, activeProjectId]);

  // Handle Projects
  const handleNewProject = useCallback(() => {
    const name = prompt("Enter project name (e.g. DBMS, Machine Learning, DSA):");
    if (!name || !name.trim()) return;
    const newProj: Project = {
      id: `proj_${Date.now()}`,
      name: name.trim(),
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setProjects((prev) => [newProj, ...prev]);
    storageAdapter.saveProject(newProj);
    setActiveProjectId(newProj.id);

    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, []);

  const handleDeleteProject = useCallback((id: string) => {
    storageAdapter.deleteProject(id);
    setProjects((prev) => prev.filter((p) => p.id !== id));
    if (activeProjectId === id) setActiveProjectId(null);
    setConversations((prev) =>
      prev.map((c) => (c.projectId === id ? { ...c, projectId: undefined } : c))
    );
  }, [activeProjectId]);

  const handleRenameProject = useCallback((id: string, newName: string) => {
    setProjects((prev) =>
      prev.map((p) => {
        if (p.id === id) {
          const updated = { ...p, name: newName, updatedAt: Date.now() };
          storageAdapter.saveProject(updated);
          return updated;
        }
        return p;
      })
    );
  }, []);

  const handleSelectProject = useCallback((id: string | null) => {
    setActiveProjectId(id);
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, []);

  // Conversation Management
  const handleTogglePinConversation = useCallback((id: string) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === id) {
          const updated = { ...c, pinned: !c.pinned, updatedAt: Date.now() };
          storageAdapter.saveConversation(updated);
          return updated;
        }
        return c;
      })
    );
  }, []);

  const handleRenameConversation = useCallback((id: string, newTitle: string) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === id) {
          const updated = { ...c, title: newTitle, updatedAt: Date.now() };
          storageAdapter.saveConversation(updated);
          return updated;
        }
        return c;
      })
    );
  }, []);

  const handleMoveConversationToProject = useCallback((convId: string, projectId?: string) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === convId) {
          const updated = { ...c, projectId: projectId, updatedAt: Date.now() };
          storageAdapter.saveConversation(updated);
          return updated;
        }
        return c;
      })
    );
  }, []);

  const handleSelectSubject = useCallback((subject: SubjectContext) => {
    setActiveSubject(subject);
    if (activeConversationId) {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConversationId) {
            const updated = { ...c, activeSubject: subject, updatedAt: Date.now() };
            storageAdapter.saveConversation(updated);
            return updated;
          }
          return c;
        })
      );
    }
  }, [activeConversationId]);

  const handleSelectModel = useCallback((modelId: string) => {
    setActiveModel(modelId);
    if (activeConversationId) {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConversationId) {
            const updated = { ...c, activeModel: modelId, updatedAt: Date.now() };
            storageAdapter.saveConversation(updated);
            return updated;
          }
          return c;
        })
      );
    }
  }, [activeConversationId]);

  const handleDeleteConversation = useCallback((id: string) => {
    storageAdapter.deleteConversation(id);
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      if (activeConversationId === id) {
        setActiveConversationId(filtered.length > 0 ? filtered[0].id : null);
      }
      return filtered;
    });
  }, [activeConversationId]);

  const handleClearAll = useCallback(() => {
    storageAdapter.clearConversations();
    setConversations([]);
    setActiveConversationId(null);
  }, []);

  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    setActiveProjectId(null); // Return to standard chat view
    const conv = conversations.find((c) => c.id === id);
    if (conv) {
      if (conv.activeSubject) setActiveSubject(conv.activeSubject);
      if (conv.activeModel) setActiveModel(conv.activeModel);
    }
    // Auto-dismiss sidebar on mobile/tablet screens
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarOpen(false);
    }
  }, [conversations]);

  // Handle message send & live streaming
  const handleSendMessage = async (promptText: string) => {
    let currentConvId = activeConversationId;
    let currentConv = activeConversation;

    if (!currentConvId || !currentConv) {
      const newConv: Conversation = {
        id: `conv_${Date.now()}`,
        title: promptText.slice(0, 30) + (promptText.length > 30 ? "..." : ""),
        messages: [],
        activeSubject: activeSubject,
        activeModel: activeModel,
        projectId: activeProjectId || undefined,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      currentConvId = newConv.id;
      currentConv = newConv;
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newConv.id);
    }

    const userMessage: Message = {
      id: `msg_user_${Date.now()}`,
      role: "user",
      content: promptText,
      timestamp: Date.now(),
      subject: activeSubject,
      model: activeModel,
    };

    const assistantMessageId = `msg_ast_${Date.now()}`;
    const initialAssistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
      subject: activeSubject,
      model: activeModel,
      status: "streaming",
    };

    const updatedMessages = [...currentConv.messages, userMessage, initialAssistantMessage];
    const updatedConv: Conversation = {
      ...currentConv,
      title: currentConv.messages.length === 0 ? promptText.slice(0, 30) + (promptText.length > 30 ? "..." : "") : currentConv.title,
      messages: updatedMessages,
      updatedAt: Date.now(),
    };

    setConversations((prev) =>
      prev.map((c) => (c.id === currentConvId ? updatedConv : c))
    );
    storageAdapter.saveConversation(updatedConv);

    setIsGenerating(true);
    const controller = new AbortController();
    activeAbortController.current = controller;

    const historyMessages = currentConv.messages.filter(
      (m) =>
        m.content &&
        m.content.trim() !== "" &&
        m.status === "complete" &&
        !m.content.includes("[Aurora System Error:") &&
        !m.content.includes("[Error:")
    );

    const recentHistory = historyMessages.slice(-6);

    await streamChatCompletion({
      messages: [...recentHistory, userMessage],
      subject: activeSubject,
      model: activeModel,
      signal: controller.signal,
      onChunk: (chunkText) => {
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === currentConvId) {
              const msgs = c.messages.map((m) => {
                if (m.id === assistantMessageId) {
                  return {
                    ...m,
                    content: m.content + chunkText,
                  };
                }
                return m;
              });
              return { ...c, messages: msgs, updatedAt: Date.now() };
            }
            return c;
          })
        );
      },
      onComplete: (fullText) => {
        setIsGenerating(false);
        activeAbortController.current = null;
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === currentConvId) {
              const msgs = c.messages.map((m) => {
                if (m.id === assistantMessageId) {
                  return {
                    ...m,
                    content: fullText || m.content,
                    status: "complete" as const,
                  };
                }
                return m;
              });
              const completedConv = { ...c, messages: msgs, updatedAt: Date.now() };
              storageAdapter.saveConversation(completedConv);
              return completedConv;
            }
            return c;
          })
        );
      },
      onError: (err) => {
        setIsGenerating(false);
        activeAbortController.current = null;
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === currentConvId) {
              const msgs = c.messages.map((m) => {
                if (m.id === assistantMessageId) {
                  return {
                    ...m,
                    content: m.content || `[Error: ${err.message}]`,
                    status: "error" as const,
                  };
                }
                return m;
              });
              return { ...c, messages: msgs, updatedAt: Date.now() };
            }
            return c;
          })
        );
      },
    });
  };

  const handleStopGeneration = () => {
    if (activeAbortController.current) {
      activeAbortController.current.abort();
      activeAbortController.current = null;
    }
    setIsGenerating(false);

    if (activeConversationId) {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConversationId) {
            const msgs = c.messages.map((m) => {
              if (m.status === "streaming") {
                return {
                  ...m,
                  status: "cancelled" as const,
                };
              }
              return m;
            });
            const updated = { ...c, messages: msgs, updatedAt: Date.now() };
            storageAdapter.saveConversation(updated);
            return updated;
          }
          return c;
        })
      );
    }
  };

  const messages = activeConversation?.messages || [];
  const projectConversations = activeProjectId
    ? conversations.filter((c) => c.projectId === activeProjectId)
    : [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100 text-slate-900 font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Sidebar Workspace */}
      <Sidebar
        conversations={conversations}
        projects={projects}
        activeConversationId={activeConversationId}
        activeProjectId={activeProjectId}
        onSelectConversation={handleSelectConversation}
        onSelectProject={handleSelectProject}
        onNewConversation={handleNewConversation}
        onNewProject={handleNewProject}
        onDeleteProject={handleDeleteProject}
        onRenameProject={handleRenameProject}
        onTogglePinConversation={handleTogglePinConversation}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        onMoveConversationToProject={handleMoveConversationToProject}
        onClearAll={handleClearAll}
        isOpen={sidebarOpen}
        onToggleOpen={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative bg-slate-50">
        <ChatHeader
          activeSubject={activeSubject}
          onSelectSubject={handleSelectSubject}
          activeModel={activeModel}
          onSelectModel={handleSelectModel}
          onNewConversation={() => handleNewConversation()}
          isGenerating={isGenerating}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          sidebarOpen={sidebarOpen}
        />

        {/* Message Container / Project View / Welcome State */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto divide-y divide-slate-200/60 scroll-smooth"
        >
          {activeProjectId && activeProject ? (
            /* PROJECT WORKSPACE VIEW */
            <div className="p-4 sm:p-8 max-w-4xl mx-auto space-y-4 sm:space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-4 gap-3">
                <div>
                  <div className="flex items-center gap-2 text-blue-600 font-semibold text-xs uppercase tracking-wider">
                    <Folder className="w-4 h-4" />
                    <span>Project Workspace</span>
                  </div>
                  <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 mt-1">
                    {activeProject.name}
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                    {activeProject.description || "Organized learning workspace"}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => handleNewConversation(activeProject.id)}
                  className="inline-flex items-center justify-center gap-2 px-3 sm:px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer shrink-0"
                >
                  <Plus className="w-4 h-4" />
                  <span>New Chat in Project</span>
                </button>
              </div>

              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Chats inside this project ({projectConversations.length})
                </h3>

                {projectConversations.length === 0 ? (
                  <div className="p-6 sm:p-8 text-center rounded-2xl bg-white border border-slate-200 space-y-3">
                    <p className="text-xs sm:text-sm text-slate-500">No chats added to this project yet.</p>
                    <button
                      type="button"
                      onClick={() => handleNewConversation(activeProject.id)}
                      className="inline-flex items-center gap-2 text-xs text-blue-600 font-semibold hover:underline cursor-pointer"
                    >
                      <Plus className="w-4 h-4" />
                      Create first chat in {activeProject.name}
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {projectConversations.map((conv) => (
                      <div
                        key={conv.id}
                        onClick={() => handleSelectConversation(conv.id)}
                        className="p-3.5 sm:p-4 rounded-xl bg-white border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all cursor-pointer space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-slate-900 font-semibold text-sm truncate">
                            <MessageSquare className="w-4 h-4 text-blue-600 shrink-0" />
                            <span className="truncate">{conv.title || "Untitled Session"}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono shrink-0 ml-2">
                            {new Date(conv.updatedAt).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 line-clamp-2">
                          {conv.messages.length > 0
                            ? conv.messages[conv.messages.length - 1].content
                            : "No messages yet"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : messages.length === 0 ? (
            /* FRESH WELCOME SCREEN IN LIGHT THEME */
            <div className="min-h-full flex flex-col items-center justify-center p-4 sm:p-6 text-center max-w-2xl mx-auto space-y-5 sm:space-y-6">
              <AuroraOrb state="idle" size="xl" />

              <div className="space-y-2 sm:space-y-3">
                <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 flex items-center justify-center gap-2">
                  Welcome to Samarthan
                  <Sparkles className="w-5 h-5 text-blue-600 shrink-0" />
                </h2>
                <p className="text-xs sm:text-sm font-semibold text-blue-600">
                  Your AI-powered educational assistant
                </p>
                <div className="pt-2 border-t border-slate-200 space-y-1">
                  <p className="text-[11px] sm:text-xs text-slate-700 font-medium">
                    Department of Computer Science and Engineering
                  </p>
                  <p className="text-[10px] sm:text-xs text-slate-500">
                    Dr. Mahalingam College of Engineering and Technology
                  </p>
                </div>
              </div>

              {/* Feature Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3 w-full text-left">
                <div className="p-3.5 sm:p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
                  <div className="flex items-center gap-1.5 text-blue-700 text-xs font-bold">
                    <GraduationCap className="w-4 h-4 shrink-0" />
                    <span>Curriculum Informed</span>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Fine-tuned on syllabus resources & textbook corpora.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
                  <div className="flex items-center gap-1.5 text-indigo-700 text-xs font-bold">
                    <Cpu className="w-4 h-4 shrink-0" />
                    <span>LoRA Specialization</span>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Independent adapter modules per computer science subject.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-1">
                  <div className="flex items-center gap-1.5 text-emerald-700 text-xs font-bold">
                    <ShieldCheck className="w-4 h-4 shrink-0" />
                    <span>Clean Architecture</span>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Decoupled storage, state persistence, and API orchestration.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            /* CONVERSATION MESSAGES LIST */
            messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
          )}
        </div>

        {/* Floating Input Area */}
        <ChatInput
          onSendMessage={handleSendMessage}
          onStopGeneration={handleStopGeneration}
          isGenerating={isGenerating}
          activeSubject={activeSubject}
        />
      </div>
    </div>
  );
}
