"use client";

import React from "react";
import { ModelSelector } from "./ModelSelector";
import { AuroraOrb } from "./AuroraOrb";
import { Plus, PanelLeft } from "lucide-react";
import { SubjectContext } from "@/types";

interface ChatHeaderProps {
  activeSubject?: SubjectContext;
  onSelectSubject?: (subject: SubjectContext) => void;
  activeModel: string;
  onSelectModel: (modelId: string) => void;
  onNewConversation: () => void;
  isGenerating: boolean;
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  activeModel,
  onSelectModel,
  onNewConversation,
  isGenerating,
  onToggleSidebar,
  sidebarOpen,
}) => {
  return (
    <header className="h-14 border-b border-slate-200 bg-white/90 backdrop-blur-md px-3 sm:px-4 flex items-center justify-between z-20 shrink-0 shadow-xs">
      {/* Left: Sidebar Toggle + Branding & Orb */}
      <div className="flex items-center gap-2 sm:gap-3">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className={`p-2 rounded-xl border border-slate-200 text-slate-600 hover:text-blue-600 hover:border-blue-300 hover:bg-slate-100 transition-all cursor-pointer ${
              sidebarOpen ? "lg:hidden" : ""
            }`}
            title="Toggle Sidebar Navigation"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}

        <AuroraOrb state={isGenerating ? "streaming" : "idle"} size="sm" />
        <div>
          <h2 className="text-xs font-bold text-slate-900 tracking-wide flex items-center gap-1.5">
            Samarthan AI
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </h2>
          <p className="text-[10px] text-slate-500 hidden xs:block sm:block">Educational Assistant</p>
        </div>
      </div>

      {/* Center / Right: Model Selector & Actions */}
      <div className="flex items-center gap-2">
        <ModelSelector
          activeModel={activeModel}
          onSelectModel={onSelectModel}
        />

        <button
          type="button"
          onClick={onNewConversation}
          className="p-1.5 sm:p-2 rounded-lg bg-slate-100 border border-slate-200 hover:border-blue-400 hover:bg-slate-200 text-slate-700 hover:text-slate-900 transition-all cursor-pointer"
          title="New Conversation"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
