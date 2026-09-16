"use client";

import React from "react";
import { ModelSelector } from "./ModelSelector";
import { AuroraOrb } from "./AuroraOrb";
import { Plus } from "lucide-react";
import { SubjectContext } from "@/types";

interface ChatHeaderProps {
  activeSubject?: SubjectContext;
  onSelectSubject?: (subject: SubjectContext) => void;
  activeModel: string;
  onSelectModel: (modelId: string) => void;
  onNewConversation: () => void;
  isGenerating: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  activeModel,
  onSelectModel,
  onNewConversation,
  isGenerating,
}) => {
  return (
    <header className="h-14 border-b border-slate-200 bg-white/90 backdrop-blur-md px-4 flex items-center justify-between z-20 shrink-0 shadow-xs">
      {/* Left: Branding & Orb */}
      <div className="flex items-center gap-3">
        <AuroraOrb state={isGenerating ? "streaming" : "idle"} size="sm" />
        <div>
          <h2 className="text-xs font-bold text-slate-900 tracking-wide flex items-center gap-1.5">
            Samarthan AI
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </h2>
          <p className="text-[10px] text-slate-500">Educational Assistant</p>
        </div>
      </div>

      {/* Center: Model Selector */}
      <div className="hidden sm:flex items-center gap-2">
        <ModelSelector
          activeModel={activeModel}
          onSelectModel={onSelectModel}
        />
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onNewConversation}
          className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 hover:border-blue-400 hover:bg-slate-200 text-slate-700 hover:text-slate-900 transition-all cursor-pointer"
          title="New Conversation"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
