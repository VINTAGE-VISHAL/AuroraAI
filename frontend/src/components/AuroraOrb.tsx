"use client";

import React from "react";

export type OrbState = "idle" | "thinking" | "streaming" | "complete";

interface AuroraOrbProps {
  state?: OrbState;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

export const AuroraOrb: React.FC<AuroraOrbProps> = ({
  state = "idle",
  size = "md",
  className = "",
}) => {
  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-12 h-12",
    lg: "w-20 h-20",
    xl: "w-28 h-28",
  }[size];

  // Calm & intelligent state styling without 360deg rotation
  const stateStyles = {
    idle: "animate-orb-idle opacity-85 shadow-[0_0_25px_rgba(147,51,234,0.3)]",
    thinking: "scale-105 shadow-[0_0_40px_rgba(59,130,246,0.6)] brightness-125 animate-orb-thinking",
    streaming: "animate-orb-streaming shadow-[0_0_35px_rgba(168,85,247,0.5)] brightness-110",
    complete: "transition-all duration-500 ease-out shadow-[0_0_20px_rgba(16,185,129,0.4)] opacity-90 scale-100",
  }[state];

  return (
    <div
      className={`relative rounded-full transition-all duration-500 ease-out flex items-center justify-center ${sizeClasses} ${stateStyles} ${className}`}
      style={{
        background:
          "radial-gradient(circle at 35% 35%, rgba(192, 132, 252, 0.95), rgba(99, 102, 241, 0.85) 45%, rgba(14, 165, 233, 0.75) 75%, rgba(15, 23, 42, 0.95))",
      }}
    >
      {/* Inner intelligent core glow */}
      <div
        className="absolute inset-1 rounded-full opacity-60 mix-blend-overlay blur-xs transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.9), transparent 70%)",
        }}
      />

      {/* Subtle pulse ring for streaming */}
      {state === "streaming" && (
        <div className="absolute -inset-1.5 rounded-full border border-purple-400/30 animate-ping opacity-20 pointer-events-none" />
      )}
    </div>
  );
};
