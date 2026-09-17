"use client";

import React, { useState, useRef, useEffect } from "react";
import { MODEL_OPTIONS } from "@/config/api";
import { ChevronDown, Cpu, ShieldCheck } from "lucide-react";

interface ModelSelectorProps {
  activeModel: string;
  onSelectModel: (modelId: string) => void;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  activeModel,
  onSelectModel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedModel =
    MODEL_OPTIONS.find((m) => m.id === activeModel) || MODEL_OPTIONS[0];

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
        aria-label="Select Model"
      >
        <Cpu className="w-3.5 h-3.5 text-blue-600" />
        <span className="text-slate-500">Model:</span>
        <span className="font-semibold text-blue-700">{selectedModel.name}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 sm:left-0 sm:right-auto mt-2 w-[calc(100vw-2rem)] max-w-72 rounded-xl bg-white border border-slate-200 shadow-xl z-50 py-1.5 divide-y divide-slate-100">
          <div className="px-3 py-1.5 flex items-center justify-between">
            <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
              Samarthan Intelligence Core
            </p>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          </div>

          <div className="py-1 max-h-80 overflow-y-auto">
            {MODEL_OPTIONS.map((model) => {
              const isSelected = model.id === activeModel;
              return (
                <button
                  key={model.id}
                  onClick={() => {
                    onSelectModel(model.id);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs flex flex-col gap-0.5 transition-colors cursor-pointer ${
                    isSelected
                      ? "bg-blue-50 text-blue-900 border-l-2 border-blue-600"
                      : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{model.name}</span>
                    {model.isDefault && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-mono font-medium">
                        Recommended
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 line-clamp-1">
                    {model.description}
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
