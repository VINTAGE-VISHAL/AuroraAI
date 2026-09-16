"use client";

import React, { useState, useRef, useEffect } from "react";
import { SubjectContext } from "@/types";
import { SUBJECT_OPTIONS } from "@/config/api";
import { ChevronDown, Sparkles, BookOpen } from "lucide-react";

interface SubjectSelectorProps {
  activeSubject: SubjectContext;
  onSelectSubject: (subject: SubjectContext) => void;
}

export const SubjectSelector: React.FC<SubjectSelectorProps> = ({
  activeSubject,
  onSelectSubject,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedOption =
    SUBJECT_OPTIONS.find((s) => s.id === activeSubject) || SUBJECT_OPTIONS[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 hover:border-blue-400 text-xs font-medium text-slate-700 hover:text-slate-900 transition-all shadow-xs backdrop-blur-md cursor-pointer"
        aria-label="Select Subject Domain"
      >
        {activeSubject === "AUTO" ? (
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
        ) : (
          <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
        )}
        <span className="text-slate-500">Subject:</span>
        <span className="font-semibold text-blue-700">{selectedOption.name}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-72 rounded-xl bg-white border border-slate-200 shadow-xl z-50 py-1.5 divide-y divide-slate-100">
          <div className="px-3 py-1.5">
            <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
              Curriculum Domain Context
            </p>
          </div>

          <div className="py-1 max-h-80 overflow-y-auto">
            {SUBJECT_OPTIONS.map((opt) => {
              const isSelected = opt.id === activeSubject;
              return (
                <button
                  key={opt.id}
                  onClick={() => {
                    onSelectSubject(opt.id);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs flex flex-col gap-0.5 transition-colors cursor-pointer ${
                    isSelected
                      ? "bg-blue-50 text-blue-900 border-l-2 border-blue-600"
                      : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{opt.name}</span>
                    {opt.id === "AUTO" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-mono font-medium">
                        Auto
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 line-clamp-1">
                    {opt.description}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
