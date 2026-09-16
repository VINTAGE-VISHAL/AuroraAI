"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Brain, Sparkles } from "lucide-react";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface ThinkingAccordionProps {
  thinking: string;
  isThinkingOpen: boolean;
  isStreaming?: boolean;
}

export const ThinkingAccordion: React.FC<ThinkingAccordionProps> = ({
  thinking,
  isThinkingOpen,
  isStreaming = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="my-2.5 rounded-lg border border-blue-200 bg-blue-50/50 overflow-hidden shadow-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-xs font-medium text-blue-800 hover:text-blue-900 bg-blue-100/60 hover:bg-blue-100 transition-all cursor-pointer select-none"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          <span className="font-semibold">Thought Process</span>
          {isThinkingOpen && isStreaming && (
            <span className="inline-flex items-center gap-1 text-[11px] text-blue-600 animate-pulse font-mono">
              <Sparkles className="w-3 h-3 animate-spin" />
              Thinking...
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 text-blue-600">
          <span className="text-[11px] opacity-75">
            {isOpen ? "Hide" : "Show"}
          </span>
          {isOpen ? (
            <ChevronDown className="w-4 h-4 transition-transform duration-200" />
          ) : (
            <ChevronRight className="w-4 h-4 transition-transform duration-200" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="p-3 border-t border-blue-200 bg-white text-xs text-slate-800 font-mono leading-relaxed overflow-x-auto max-h-96 overflow-y-auto">
          <MarkdownRenderer content={thinking} isStreaming={isStreaming} />
        </div>
      )}
    </div>
  );
};
