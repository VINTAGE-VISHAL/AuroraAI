"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Square, Sparkles, Mic, MicOff, Loader2, Paperclip, FileText, Check, X, AlertCircle } from "lucide-react";
import { RuntimeFile, SubjectContext } from "@/types";
import { transcribeAudioBlob, uploadFile } from "@/services/api";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onStopGeneration: () => void;
  isGenerating: boolean;
  activeSubject: SubjectContext;
  conversationId?: string | null;
}


const DOMAIN_PROMPT_SUGGESTIONS: Record<SubjectContext, string[]> = {
  AUTO: [
    "Explain standard database transaction isolation levels",
    "What is the time complexity of QuickSort vs MergeSort?",
    "Explain SOLID principles with code examples",
  ],
  DBMS: [
    "Explain 3NF vs BCNF normalization with examples",
    "Write a SQL query utilizing JOIN and GROUP BY with HAVING",
    "Explain ACID properties in relational databases",
  ],
  DSA: [
    "Explain Binary Search Tree insertion algorithm",
    "How to detect a cycle in a Directed Graph using DFS?",
    "Compare Dynamic Programming vs Greedy approaches",
  ],
  OOPS: [
    "Explain Method Overriding vs Overloading in Java/Python",
    "Demonstrate Factory Design Pattern implementation",
    "What is Encapsulation and why is it essential?",
  ],
  OS: [
    "Explain Banker's Algorithm for Deadlock Avoidance",
    "What is the difference between Process and Thread?",
    "Explain Paging vs Segmentation in Memory Management",
  ],
  CNT: [
    "Explain the 7 layers of OSI Model with functions",
    "How does TCP 3-Way Handshake establish connection?",
    "Explain Subnetting and IPv4 CIDR notation",
  ],
  OOSE: [
    "Explain Agile Scrum Framework ceremonies and roles",
    "Draw UML Sequence Diagram for user authentication",
    "What is Black Box vs White Box Testing?",
  ],
};

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onStopGeneration,
  isGenerating,
  activeSubject,
  conversationId,
}) => {
  const [input, setInput] = useState("");
  const [sttState, setSttState] = useState<"idle" | "recording" | "transcribing">("idle");
  const [attachedFile, setAttachedFile] = useState<{
    file_id?: string;
    filename: string;
    size_bytes: number;
    status: "uploading" | "stored" | "failed";
    error?: string;
  } | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input element so selecting the same file again triggers change
    e.target.value = "";

    // Client-side quick extension check (.pdf, .docx, .txt, .md)
    const allowedExtensions = [".pdf", ".docx", ".txt", ".md"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      setAttachedFile({
        filename: file.name,
        size_bytes: file.size,
        status: "failed",
        error: `Unsupported file type (${ext}). Please attach PDF, DOCX, TXT, or MD.`,
      });
      return;
    }

    // Client-side quick size check (20 MB default)
    const maxBytes = 20 * 1024 * 1024;
    if (file.size > maxBytes) {
      setAttachedFile({
        filename: file.name,
        size_bytes: file.size,
        status: "failed",
        error: "File size exceeds 20 MB limit.",
      });
      return;
    }

    const effectiveConvId = conversationId || "default_session";
    setAttachedFile({
      filename: file.name,
      size_bytes: file.size,
      status: "uploading",
    });

    try {
      const response = await uploadFile(file, effectiveConvId);
      setAttachedFile({
        file_id: response.file_id,
        filename: response.filename,
        size_bytes: response.size_bytes,
        status: "stored",
      });
    } catch (err: any) {
      console.warn("File upload failed:", err);
      setAttachedFile({
        filename: file.name,
        size_bytes: file.size,
        status: "failed",
        error: err.message || "Upload failed. Please check backend status.",
      });
    }
  };

  const handleRemoveAttachment = () => {
    setAttachedFile(null);
  };


  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Microphone recording is not supported in your browser or connection environment.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const options = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? { mimeType: "audio/webm;codecs=opus" }
        : MediaRecorder.isTypeSupported("audio/webm")
        ? { mimeType: "audio/webm" }
        : MediaRecorder.isTypeSupported("audio/mp4")
        ? { mimeType: "audio/mp4" }
        : undefined;

      const mediaRecorder = new MediaRecorder(stream, options);

      mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || "audio/webm",
        });

        if (audioBlob.size < 500) {
          setSttState("idle");
          return;
        }

        setSttState("transcribing");

        try {
          const result = await transcribeAudioBlob(audioBlob);
          const transcribedText = result?.text?.trim() || "";

          if (transcribedText) {
            setInput((prev) => {
              const trimmed = prev.trim();
              return trimmed ? `${trimmed} ${transcribedText}` : transcribedText;
            });
          } else {
            console.info("No speech recognized in audio recording.");
          }
        } catch (err: any) {
          console.warn("Speech transcription failed:", err);
          alert("Transcription service encountered an error. Please verify backend status.");
        } finally {
          setSttState("idle");
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250);
      setSttState("recording");
    } catch (err: any) {
      setSttState("idle");
      console.warn("Microphone access error:", err);
      if (err?.name === "NotFoundError" || err?.message?.includes("Requested device not found")) {
        alert("No microphone hardware detected on your computer.");
      } else {
        alert("Microphone access is currently blocked by your browser settings.");
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleRecording = () => {
    if (sttState === "recording") {
      stopRecording();
    } else if (sttState === "idle") {
      startRecording();
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isGenerating) return;
    if (sttState === "recording") {
      stopRecording();
    }
    onSendMessage(input.trim());
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const suggestions = DOMAIN_PROMPT_SUGGESTIONS[activeSubject] || DOMAIN_PROMPT_SUGGESTIONS.AUTO;

  return (
    <div className="w-full max-w-4xl mx-auto px-2 sm:px-4 pb-3 sm:pb-4 font-sans">
      {/* Quick Prompt Suggestions */}
      {!isGenerating && input.length === 0 && sttState === "idle" && (
        <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto py-1.5 sm:py-2 mb-1.5 sm:mb-2 scrollbar-none no-scrollbar">
          <Sparkles className="w-3.5 h-3.5 text-blue-600 shrink-0 ml-1" />
          {suggestions.map((promptText, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setInput(promptText);
                if (textareaRef.current) textareaRef.current.focus();
              }}
              className="px-2.5 py-1 rounded-full bg-white border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 text-[11px] sm:text-xs text-slate-700 hover:text-blue-700 whitespace-nowrap transition-colors cursor-pointer shadow-2xs shrink-0"
            >
              {promptText}
            </button>
          ))}
        </div>
      )}

      {/* Attachment Preview Badge */}
      {attachedFile && (
        <div className="mb-2 flex items-center gap-2 p-2 rounded-xl bg-white border border-slate-200 shadow-2xs text-xs">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {attachedFile.status === "uploading" ? (
              <Loader2 className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
            ) : attachedFile.status === "stored" ? (
              <Check className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <FileText className="w-4 h-4 text-slate-500 shrink-0" />
            <span className="font-medium text-slate-800 truncate">
              {attachedFile.filename}
            </span>
            <span className="text-[11px] text-slate-400 shrink-0">
              ({(attachedFile.size_bytes / 1024).toFixed(1)} KB)
            </span>
            {attachedFile.status === "uploading" && (
              <span className="text-[11px] text-blue-600 font-medium">Uploading...</span>
            )}
            {attachedFile.status === "stored" && (
              <span className="text-[11px] text-emerald-600 font-medium">Stored</span>
            )}
            {attachedFile.status === "failed" && (
              <span className="text-[11px] text-rose-600 font-medium">
                {attachedFile.error || "Upload failed"}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={handleRemoveAttachment}
            className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 cursor-pointer transition-colors"
            title="Remove attachment"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Hidden Native File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Input Box Container */}
      <form
        onSubmit={handleSubmit}
        className="relative rounded-2xl bg-white border border-slate-200 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 shadow-lg transition-all p-1.5 sm:p-2 flex items-end gap-1.5 sm:gap-2"
      >
        {/* Attachment Paperclip Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isGenerating || attachedFile?.status === "uploading"}
          className="p-2.5 rounded-xl transition-all cursor-pointer shrink-0 bg-slate-100 text-slate-500 border border-slate-200 hover:text-slate-800 hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Attach document (.pdf, .docx, .txt, .md)"
        >
          <Paperclip className="w-4 h-4" />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sttState === "transcribing"}
          placeholder={
            sttState === "recording"
              ? "Recording voice... Click mic when finished."
              : sttState === "transcribing"
              ? "Transcribing speech..."
              : `Ask Samarthan (${activeSubject === "AUTO" ? "Auto Detect" : activeSubject})...`
          }
          rows={1}
          className="flex-1 bg-transparent border-0 resize-none px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:outline-none max-h-40 min-h-[38px] sm:min-h-[42px] leading-relaxed disabled:opacity-50"
        />

        {/* Speech Dictation Button */}

        <button
          type="button"
          onClick={toggleRecording}
          disabled={sttState === "transcribing"}
          className={`p-2.5 rounded-xl transition-all cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed ${
            sttState === "recording"
              ? "bg-red-100 text-red-600 border border-red-300 animate-pulse shadow-sm"
              : sttState === "transcribing"
              ? "bg-blue-100 text-blue-600 border border-blue-300"
              : "bg-slate-100 text-slate-500 border border-slate-200 hover:text-slate-800 hover:bg-slate-200"
          }`}
          title={
            sttState === "recording"
              ? "Stop Voice Recording"
              : sttState === "transcribing"
              ? "Transcribing Audio..."
              : "Start Voice Input"
          }
        >
          {sttState === "transcribing" ? (
            <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          ) : sttState === "recording" ? (
            <MicOff className="w-4 h-4 text-red-600" />
          ) : (
            <Mic className="w-4 h-4" />
          )}
        </button>

        {/* Action Button: Send or Stop */}
        {isGenerating ? (
          <button
            type="button"
            onClick={onStopGeneration}
            className="p-2.5 rounded-xl bg-amber-100 text-amber-800 border border-amber-300 hover:bg-amber-200 transition-all cursor-pointer shrink-0 flex items-center gap-1.5 text-xs font-semibold"
            title="Stop Generation"
          >
            <Square className="w-4 h-4 fill-amber-700" />
            <span className="hidden sm:inline">Stop</span>
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim() || sttState === "transcribing"}
            className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 text-white transition-all cursor-pointer shrink-0 shadow-sm disabled:cursor-not-allowed"
            title="Send Prompt"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>

      <p className="text-[11px] text-center text-slate-500 mt-2">
        Samarthan transforms trusted educational resources into domain-specific curriculum intelligence.
      </p>
    </div>
  );
};
