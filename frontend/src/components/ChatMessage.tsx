"use client";

import React, { useState, useEffect } from "react";
import { Message } from "@/types";
import { AuroraOrb } from "./AuroraOrb";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { User, Copy, Check, Volume2, VolumeX, Ban, FileText, BookOpen, ChevronDown, ChevronRight } from "lucide-react";
import { SUBJECT_OPTIONS } from "@/config/api";

import { parseThinkingContent } from "@/utils/thinkParser";
import { ThinkingAccordion } from "./ThinkingAccordion";
import { selectBestFemaleEnglishVoice } from "@/utils/voiceSelector";

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isCitationsOpen, setIsCitationsOpen] = useState(false);

  const isUser = message.role === "user";
  const isStreaming = message.status === "streaming";
  const isCancelled = message.status === "cancelled";

  const parsedContent = React.useMemo(
    () => (isUser ? { thinking: null, content: message.content, isThinkingOpen: false } : parseThinkingContent(message.content)),
    [isUser, message.content]
  );

  const subjectBadge = message.subject
    ? SUBJECT_OPTIONS.find((s) => s.id === message.subject)
    : null;

  // Cleanup speech synthesis on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleToggleSpeak = () => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      alert("Text-to-speech is not supported in your browser.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    // Cancel any current ongoing speech synthesis playback
    window.speechSynthesis.cancel();

    // Strip markdown formatting symbols and think blocks for clean audio reading
    const textToRead = parsedContent.content
      .replace(/<think>[\s\S]*?<\/think>/gi, "")
      .replace(/```[\s\S]*?```/g, "Code block omitted.")
      .replace(/[*_#`~>\[\]\(\)]/g, "")
      .trim();

    if (!textToRead) return;

    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.rate = 0.98;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Dynamically select best available female English voice (preferring en-IN)
    const selectedVoice = selectBestFemaleEnglishVoice();
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const formattedTime = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div

      className={`py-3 sm:py-4 px-2.5 sm:px-6 transition-colors w-full overflow-hidden ${
        isUser
          ? "bg-blue-50/60 border-y border-blue-100/80"
          : "bg-white border-y border-slate-100"
      }`}
    >
      <div className="max-w-4xl mx-auto flex gap-2 sm:gap-4 w-full min-w-0">
        {/* Avatar */}
        <div className="shrink-0 mt-0.5">
          {isUser ? (
            <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <User className="w-3 h-3 sm:w-4 sm:h-4" />
            </div>
          ) : (
            <div className="w-6 h-6 sm:w-8 sm:h-8 flex items-center justify-center">
              <AuroraOrb state={isStreaming ? "streaming" : "idle"} size="sm" className="!w-6 !h-6 sm:!w-8 sm:!h-8" />
            </div>
          )}
        </div>

        {/* Content Container */}
        <div className="flex-1 min-w-0 space-y-1.5 sm:space-y-2 overflow-hidden">
          {/* Header Metadata */}
          <div className="flex items-center justify-between gap-1 text-[11px] sm:text-xs text-slate-500">
            <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 truncate">
              <span className="font-bold text-slate-900 shrink-0">
                {isUser ? "You" : "Samarthan AI"}
              </span>

              {subjectBadge && !isUser && (
                <span
                  className="text-[9px] sm:text-[10px] px-1.5 py-0.5 rounded-full border font-mono bg-blue-50 text-blue-700 border-blue-200 truncate max-w-[120px] sm:max-w-none"
                >
                  {subjectBadge.name}
                </span>
              )}

              {message.model && !isUser && (
                <span className="text-[9px] sm:text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono hidden md:inline-block">
                  {message.model}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1 sm:gap-2 shrink-0">
              <span className="text-[9px] sm:text-[11px] text-slate-400">{formattedTime}</span>

              {/* Text to Speech Button */}
              {!isUser && parsedContent.content && !isStreaming && (
                <button
                  type="button"
                  onClick={handleToggleSpeak}
                  className={`p-1 rounded transition-colors cursor-pointer ${
                    isSpeaking
                      ? "text-blue-600 bg-blue-100 animate-pulse"
                      : "text-slate-400 hover:text-slate-700"
                  }`}
                  title={isSpeaking ? "Stop Read Aloud" : "Read Aloud"}
                >
                  {isSpeaking ? <VolumeX className="w-3.5 h-3.5 text-blue-600" /> : <Volume2 className="w-3.5 h-3.5" />}
                </button>
              )}

              <button
                type="button"
                onClick={handleCopy}
                className="text-slate-400 hover:text-slate-700 transition-colors p-1 rounded cursor-pointer"
                title="Copy Message"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Attached Document Metadata Chip (if present on user message) */}
          {isUser && message.attachment && (
            <div className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-blue-100/70 border border-blue-200/80 text-blue-900 text-xs shadow-2xs max-w-full">
              <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span className="font-medium truncate max-w-[200px] sm:max-w-md" title={message.attachment.filename}>
                {message.attachment.filename}
              </span>
              {message.attachment.fileType && (
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-blue-200/60 text-blue-800 shrink-0 font-semibold">
                  {message.attachment.fileType}
                </span>
              )}
              {message.attachment.sizeBytes !== undefined && (
                <span className="text-[10px] text-blue-600/80 shrink-0 hidden sm:inline">
                  ({(message.attachment.sizeBytes / 1024).toFixed(1)} KB)
                </span>
              )}
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-700 font-medium shrink-0 flex items-center gap-1 border border-emerald-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Indexed
              </span>
            </div>
          )}

          {/* Body Content */}
          <div className="relative space-y-2 w-full overflow-hidden">
            {parsedContent.thinking && (
              <ThinkingAccordion
                thinking={parsedContent.thinking}
                isThinkingOpen={parsedContent.isThinkingOpen}
                isStreaming={isStreaming}
              />
            )}
            {parsedContent.content ? (
              <MarkdownRenderer content={parsedContent.content} isStreaming={isStreaming} />
            ) : isStreaming && parsedContent.isThinkingOpen ? (
              <div className="text-xs text-blue-600 animate-pulse italic py-1">
                Thinking in progress...
              </div>
            ) : null}

            {/* Cancelled Marker */}
            {isCancelled && (
              <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-50 border border-amber-200 text-amber-700 text-xs">
                <Ban className="w-3.5 h-3.5" />
                <span>Generation stopped by user</span>
              </div>
            )}

            {/* Source Citations Accordion (Assistant RAG responses) */}
            {!isUser && message.citations && message.citations.length > 0 && (
              <div className="mt-3 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCitationsOpen((prev) => !prev)}
                  className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-blue-700 cursor-pointer transition-colors group"
                >
                  <BookOpen className="w-3.5 h-3.5 text-blue-600 group-hover:scale-105 transition-transform" />
                  <span>
                    Sources ({message.citations.length})
                  </span>
                  {isCitationsOpen ? (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600" />
                  )}
                </button>

                {isCitationsOpen && (
                  <div className="mt-2 space-y-1.5">
                    {message.citations.map((cit, idx) => (
                      <div
                        key={cit.chunk_id || idx}
                        className="p-2 rounded-lg bg-slate-50 border border-slate-200/80 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 shadow-2xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-[10px] font-semibold text-blue-700 px-1.5 py-0.5 rounded bg-blue-100/70 border border-blue-200 shrink-0">
                            {cit.label || `[Source ${idx + 1}]`}
                          </span>
                          <FileText className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="font-medium text-slate-800 truncate max-w-[200px] sm:max-w-xs" title={cit.filename}>
                            {cit.filename}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-[11px] text-slate-500 shrink-0 ml-6 sm:ml-0">
                          {cit.source_page !== null && cit.source_page !== undefined && (
                            <span className="px-1.5 py-0.2 rounded bg-slate-200/70 text-slate-700 font-mono text-[10px]">
                              Page {cit.source_page}
                            </span>
                          )}
                          {cit.relevance_score !== undefined && (
                            <span className="text-[10px] text-emerald-700 font-mono bg-emerald-50 border border-emerald-200/60 px-1.5 py-0.2 rounded">
                              {Math.round(cit.relevance_score * 100)}% match
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


