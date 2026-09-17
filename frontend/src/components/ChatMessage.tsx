"use client";

import React, { useState, useEffect } from "react";
import { Message } from "@/types";
import { AuroraOrb } from "./AuroraOrb";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { User, Copy, Check, Volume2, VolumeX, Ban } from "lucide-react";
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
      className={`py-3.5 px-3 sm:px-6 transition-colors ${
        isUser
          ? "bg-blue-50/60 border-y border-blue-100/80"
          : "bg-white border-y border-slate-100"
      }`}
    >
      <div className="max-w-4xl mx-auto flex gap-2.5 sm:gap-4">
        {/* Avatar */}
        <div className="shrink-0 mt-0.5">
          {isUser ? (
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <User className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </div>
          ) : (
            <AuroraOrb state={isStreaming ? "streaming" : "idle"} size="sm" />
          )}
        </div>

        {/* Content Container */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Header Metadata */}
          <div className="flex flex-wrap items-center justify-between gap-1.5 text-xs text-slate-500">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <span className="font-bold text-slate-900">
                {isUser ? "You" : "Samarthan AI"}
              </span>

              {subjectBadge && !isUser && (
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full border font-mono bg-blue-50 text-blue-700 border-blue-200"
                >
                  {subjectBadge.name}
                </span>
              )}

              {message.model && !isUser && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono hidden xs:inline-block">
                  {message.model}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
              <span className="text-[10px] sm:text-[11px] text-slate-400 mr-0.5">{formattedTime}</span>

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

          {/* Body Content */}
          <div className="relative space-y-2">
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
          </div>
        </div>
      </div>
    </div>
  );
};
