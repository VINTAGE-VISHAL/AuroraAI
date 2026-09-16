"use client";

import React from "react";
import { Conversation } from "@/types";
import { Plus, MessageSquare, Trash2, PanelLeftClose, PanelLeft, Pin, Search, Folder, ChevronDown, ChevronRight, Settings, MoreVertical, Edit2 } from "lucide-react";

interface SidebarProps {
  conversations: Conversation[];
  projects: { id: string; name: string; description?: string }[];
  activeConversationId: string | null;
  activeProjectId: string | null;
  onSelectConversation: (id: string) => void;
  onSelectProject: (id: string | null) => void;
  onNewConversation: (projectId?: string) => void;
  onNewProject: () => void;
  onDeleteProject: (id: string) => void;
  onRenameProject: (id: string, newName: string) => void;
  onTogglePinConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  onMoveConversationToProject: (convId: string, projectId?: string) => void;
  onClearAll: () => void;
  isOpen: boolean;
  onToggleOpen: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  projects,
  activeConversationId,
  activeProjectId,
  onSelectConversation,
  onSelectProject,
  onNewConversation,
  onNewProject,
  onDeleteProject,
  onRenameProject,
  onTogglePinConversation,
  onRenameConversation,
  onDeleteConversation,
  onMoveConversationToProject,
  onClearAll,
  isOpen,
  onToggleOpen,
}) => {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [expandedProjects, setExpandedProjects] = React.useState<Record<string, boolean>>({});
  const [activeMenuConvId, setActiveMenuConvId] = React.useState<string | null>(null);
  const [activeMenuProjId, setActiveMenuProjId] = React.useState<string | null>(null);

  // Close context menus when clicking outside
  React.useEffect(() => {
    const handleOutside = () => {
      setActiveMenuConvId(null);
      setActiveMenuProjId(null);
    };
    window.addEventListener("click", handleOutside);
    return () => window.removeEventListener("click", handleOutside);
  }, []);

  const toggleProjectExpand = (id: string) => {
    setExpandedProjects((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Filter conversations by search term
  const filteredConversations = React.useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const query = searchQuery.toLowerCase().trim();
    return conversations.filter(
      (c) =>
        c.title.toLowerCase().includes(query) ||
        c.messages.some((m) => m.content.toLowerCase().includes(query))
    );
  }, [conversations, searchQuery]);

  // Separate conversations into Pinned, Project-bound, and Recent
  const pinnedChats = filteredConversations.filter((c) => c.pinned);
  const recentChats = filteredConversations.filter((c) => !c.pinned && !c.projectId);

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={onToggleOpen}
        className="fixed top-3 left-3 z-40 p-2.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:border-blue-300 shadow-md backdrop-blur-md transition-all cursor-pointer"
        title="Open Workspace Sidebar"
      >
        <PanelLeft className="w-5 h-5" />
      </button>
    );
  }

  return (
    <aside className="w-72 h-full bg-slate-50/95 border-r border-slate-200 flex flex-col z-30 shadow-sm shrink-0 transition-all font-sans text-slate-800">
      {/* 1. TOP BRANDING AREA */}
      <div className="p-4 border-b border-slate-200/80 flex flex-col gap-3 bg-white/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="/mcet_logo.png"
              alt="Dr. Mahalingam College of Engineering and Technology Logo"
              className="h-16 w-auto object-contain shrink-0 max-w-[140px]"
            />
          </div>
          <button
            type="button"
            onClick={onToggleOpen}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-200/60 transition-colors cursor-pointer"
            title="Collapse Sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
        <div>
          <h1 className="text-base font-extrabold text-slate-900 tracking-wide">
            SAMARTHAN
          </h1>
          <p className="text-xs text-blue-600 font-semibold">AI Educational Assistant</p>
        </div>
      </div>

      {/* 2. PRIMARY ACTIONS (+ New Chat & Search) */}
      <div className="p-3 border-b border-slate-200/60 space-y-2 bg-white/40">
        <button
          type="button"
          onClick={() => onNewConversation()}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>

        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-3 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
          />
        </div>
      </div>

      {/* SIDEBAR NAVIGATION BODY */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-4">
        {/* 3. PINNED SECTION */}
        <div>
          <div className="px-2 pb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            <Pin className="w-3 h-3 text-blue-600" />
            <span>Pinned</span>
          </div>

          {pinnedChats.length === 0 ? (
            <div className="px-3 py-1 text-[11px] text-slate-400 italic">No pinned chats</div>
          ) : (
            <div className="space-y-0.5">
              {pinnedChats.map((conv) => (
                <ChatItemRow
                  key={conv.id}
                  conv={conv}
                  isActive={conv.id === activeConversationId}
                  projects={projects}
                  activeMenuConvId={activeMenuConvId}
                  setActiveMenuConvId={setActiveMenuConvId}
                  onSelectConversation={onSelectConversation}
                  onTogglePinConversation={onTogglePinConversation}
                  onRenameConversation={onRenameConversation}
                  onDeleteConversation={onDeleteConversation}
                  onMoveConversationToProject={onMoveConversationToProject}
                />
              ))}
            </div>
          )}
        </div>

        {/* 4. PROJECTS SECTION */}
        <div>
          <div className="px-2 pb-1.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <Folder className="w-3 h-3 text-blue-600" />
              <span>Projects</span>
            </div>
            <button
              type="button"
              onClick={onNewProject}
              className="p-1 rounded text-slate-500 hover:text-blue-600 hover:bg-slate-200/60 transition-colors cursor-pointer"
              title="New Project Workspace"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>

          {projects.length === 0 ? (
            <div className="px-3 py-1 text-[11px] text-slate-400 italic">No projects created</div>
          ) : (
            <div className="space-y-1">
              {projects.map((project) => {
                const isExpanded = !!expandedProjects[project.id];
                const isProjActive = activeProjectId === project.id;
                const projChats = filteredConversations.filter((c) => c.projectId === project.id);

                return (
                  <div key={project.id} className="space-y-0.5">
                    {/* Project Header Item */}
                    <div
                      className={`group relative flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                        isProjActive
                          ? "bg-blue-100/80 text-blue-900 font-semibold border border-blue-200"
                          : "text-slate-700 hover:bg-slate-200/50"
                      }`}
                      onClick={() => {
                        onSelectProject(project.id);
                        setExpandedProjects((prev) => ({ ...prev, [project.id]: true }));
                      }}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleProjectExpand(project.id);
                          }}
                          className="p-0.5 rounded text-slate-500 hover:text-slate-800"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                        </button>
                        <Folder className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                        <span className="truncate">{project.name}</span>
                      </div>

                      {/* Project Context Menu */}
                      <div className="relative">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveMenuProjId(activeMenuProjId === project.id ? null : project.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-400 hover:text-slate-700 transition-opacity"
                        >
                          <MoreVertical className="w-3 h-3" />
                        </button>

                        {activeMenuProjId === project.id && (
                          <div
                            className="absolute right-0 top-6 w-36 bg-white border border-slate-200 shadow-xl rounded-lg py-1 z-50 text-xs font-normal"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <button
                              type="button"
                              onClick={() => {
                                onNewConversation(project.id);
                                setActiveMenuProjId(null);
                              }}
                              className="w-full px-3 py-1.5 text-left hover:bg-slate-100 flex items-center gap-2"
                            >
                              <Plus className="w-3.5 h-3.5 text-blue-600" />
                              <span>New Chat</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                const val = prompt("Rename project workspace:", project.name);
                                if (val && val.trim()) onRenameProject(project.id, val.trim());
                                setActiveMenuProjId(null);
                              }}
                              className="w-full px-3 py-1.5 text-left hover:bg-slate-100 flex items-center gap-2"
                            >
                              <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                              <span>Rename</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                if (confirm(`Delete project "${project.name}"?`)) {
                                  onDeleteProject(project.id);
                                }
                                setActiveMenuProjId(null);
                              }}
                              className="w-full px-3 py-1.5 text-left text-rose-600 hover:bg-rose-50 flex items-center gap-2"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Delete</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Expandable Project Conversations */}
                    {isExpanded && (
                      <div className="pl-6 space-y-0.5 border-l-2 border-slate-200 ml-3">
                        {projChats.length === 0 ? (
                          <div className="py-1 text-[11px] text-slate-400 italic">Empty project</div>
                        ) : (
                          projChats.map((conv) => (
                            <ChatItemRow
                              key={conv.id}
                              conv={conv}
                              isActive={conv.id === activeConversationId}
                              projects={projects}
                              activeMenuConvId={activeMenuConvId}
                              setActiveMenuConvId={setActiveMenuConvId}
                              onSelectConversation={onSelectConversation}
                              onTogglePinConversation={onTogglePinConversation}
                              onRenameConversation={onRenameConversation}
                              onDeleteConversation={onDeleteConversation}
                              onMoveConversationToProject={onMoveConversationToProject}
                            />
                          ))
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 5. RECENT CHATS SECTION */}
        <div>
          <div className="px-2 pb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            <MessageSquare className="w-3 h-3 text-blue-600" />
            <span>Recent</span>
          </div>

          {recentChats.length === 0 ? (
            <div className="px-3 py-2 text-center text-xs text-slate-400">
              {searchQuery ? "No conversations found" : "No recent chats"}
            </div>
          ) : (
            <div className="space-y-0.5">
              {recentChats.map((conv) => (
                <ChatItemRow
                  key={conv.id}
                  conv={conv}
                  isActive={conv.id === activeConversationId}
                  projects={projects}
                  activeMenuConvId={activeMenuConvId}
                  setActiveMenuConvId={setActiveMenuConvId}
                  onSelectConversation={onSelectConversation}
                  onTogglePinConversation={onTogglePinConversation}
                  onRenameConversation={onRenameConversation}
                  onDeleteConversation={onDeleteConversation}
                  onMoveConversationToProject={onMoveConversationToProject}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 6. BOTTOM SETTINGS FOOTER */}
      <div className="p-3 border-t border-slate-200/80 bg-white/60 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-slate-400" />
          <span className="font-medium">Samarthan v2.5</span>
        </div>

        {conversations.length > 0 && (
          <button
            type="button"
            onClick={onClearAll}
            className="text-[11px] text-slate-400 hover:text-rose-600 transition-colors cursor-pointer"
          >
            Clear All
          </button>
        )}
      </div>
    </aside>
  );
};

interface ChatItemRowProps {
  conv: Conversation;
  isActive: boolean;
  projects: { id: string; name: string }[];
  activeMenuConvId: string | null;
  setActiveMenuConvId: (id: string | null) => void;
  onSelectConversation: (id: string) => void;
  onTogglePinConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onDeleteConversation: (id: string) => void;
  onMoveConversationToProject: (convId: string, projectId?: string) => void;
}

const ChatItemRow: React.FC<ChatItemRowProps> = ({
  conv,
  isActive,
  projects,
  activeMenuConvId,
  setActiveMenuConvId,
  onSelectConversation,
  onTogglePinConversation,
  onRenameConversation,
  onDeleteConversation,
  onMoveConversationToProject,
}) => {
  const isMenuOpen = activeMenuConvId === conv.id;

  return (
    <div
      className={`group relative flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-colors cursor-pointer ${
        isActive
          ? "bg-blue-600 text-white font-medium shadow-xs"
          : "text-slate-700 hover:bg-slate-200/60"
      }`}
      onClick={() => onSelectConversation(conv.id)}
    >
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <MessageSquare
          className={`w-3.5 h-3.5 shrink-0 ${
            isActive ? "text-white" : "text-blue-600"
          }`}
        />
        <span className="truncate">{conv.title || "Untitled Session"}</span>
      </div>

      <div className="relative flex items-center gap-1">
        {conv.pinned && (
          <Pin className={`w-3 h-3 ${isActive ? "text-blue-200" : "text-blue-600"}`} />
        )}

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setActiveMenuConvId(isMenuOpen ? null : conv.id);
          }}
          className={`p-1 rounded transition-opacity ${
            isActive
              ? "text-blue-100 hover:text-white hover:bg-blue-700"
              : "opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-700 hover:bg-slate-200"
          }`}
          title="Options"
        >
          <MoreVertical className="w-3.5 h-3.5" />
        </button>

        {isMenuOpen && (
          <div
            className="absolute right-0 top-7 w-44 bg-white border border-slate-200 shadow-xl rounded-lg py-1 z-50 text-xs font-normal text-slate-800"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => {
                onTogglePinConversation(conv.id);
                setActiveMenuConvId(null);
              }}
              className="w-full px-3 py-1.5 text-left hover:bg-slate-100 flex items-center gap-2"
            >
              <Pin className="w-3 h-3 text-blue-600" />
              <span>{conv.pinned ? "Unpin chat" : "Pin chat"}</span>
            </button>

            <button
              type="button"
              onClick={() => {
                const title = prompt("Rename session:", conv.title);
                if (title && title.trim()) onRenameConversation(conv.id, title.trim());
                setActiveMenuConvId(null);
              }}
              className="w-full px-3 py-1.5 text-left hover:bg-slate-100 flex items-center gap-2"
            >
              <Edit2 className="w-3.5 h-3.5 text-slate-500" />
              <span>Rename</span>
            </button>

            {/* Move to Project submenu if projects exist */}
            {projects.length > 0 && (
              <div className="border-t border-slate-100 py-1">
                <p className="px-3 py-0.5 text-[10px] font-semibold text-slate-400 uppercase">
                  Assign Project
                </p>
                <button
                  type="button"
                  onClick={() => {
                    onMoveConversationToProject(conv.id, undefined);
                    setActiveMenuConvId(null);
                  }}
                  className={`w-full px-3 py-1 text-left text-[11px] hover:bg-slate-100 ${
                    !conv.projectId ? "font-bold text-blue-600" : "text-slate-600"
                  }`}
                >
                  (No Project)
                </button>
                {projects.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      onMoveConversationToProject(conv.id, p.id);
                      setActiveMenuConvId(null);
                    }}
                    className={`w-full px-3 py-1 text-left text-[11px] hover:bg-slate-100 truncate ${
                      conv.projectId === p.id ? "font-bold text-blue-600" : "text-slate-600"
                    }`}
                  >
                    📁 {p.name}
                  </button>
                ))}
              </div>
            )}

            <div className="border-t border-slate-100 pt-1">
              <button
                type="button"
                onClick={() => {
                  onDeleteConversation(conv.id);
                  setActiveMenuConvId(null);
                }}
                className="w-full px-3 py-1.5 text-left text-rose-600 hover:bg-rose-50 flex items-center gap-2"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
