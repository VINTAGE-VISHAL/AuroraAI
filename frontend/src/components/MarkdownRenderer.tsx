"use client";

import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  isStreaming = false,
}) => {
  const markdownPlugins = useMemo(() => {
    if (isStreaming) {
      return { remarkPlugins: [], rehypePlugins: [] };
    }
    return {
      remarkPlugins: [remarkMath],
      rehypePlugins: [rehypeKatex],
    };
  }, [isStreaming]);

  return (
    <div className="prose max-w-none text-slate-800 text-xs sm:text-sm leading-relaxed tracking-normal break-words">
      <ReactMarkdown
        remarkPlugins={markdownPlugins.remarkPlugins}
        rehypePlugins={markdownPlugins.rehypePlugins}
        components={{
          h1({ children }) {
            return (
              <h1 className="text-base sm:text-lg font-bold text-slate-950 mt-3 mb-1.5 pb-1 border-b border-slate-200">
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return (
              <h2 className="text-sm sm:text-base font-bold text-slate-900 mt-2.5 mb-1 text-blue-900">
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return (
              <h3 className="text-xs sm:text-sm font-semibold text-slate-900 mt-2 mb-1">
                {children}
              </h3>
            );
          },
          h4({ children }) {
            return (
              <h4 className="text-xs sm:text-xs font-semibold text-slate-800 mt-1.5 mb-0.5">
                {children}
              </h4>
            );
          },
          p({ children }) {
            return <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>;
          },
          ul({ children }) {
            return <ul className="my-1.5 list-disc list-outside pl-4 space-y-1">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-1.5 list-decimal list-outside pl-4 space-y-1">{children}</ol>;
          },
          li({ children }) {
            return <li className="pl-0.5 leading-relaxed">{children}</li>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-2 border-l-2 sm:border-l-3 border-blue-500 bg-blue-50/50 pl-3 py-1 text-slate-700 italic rounded-r-md">
                {children}
              </blockquote>
            );
          },
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const codeString = String(children).replace(/\n$/, "");

            if (!inline && match) {
              return (
                <div className="relative my-2 sm:my-3 rounded-lg sm:rounded-xl overflow-hidden border border-slate-800 bg-slate-950 text-slate-100 shadow-xs max-w-full">
                  <div className="flex items-center justify-between px-2.5 sm:px-3 py-1 bg-slate-900 border-b border-slate-800 text-[10px] sm:text-xs font-mono text-slate-400">
                    <span className="uppercase">{match[1]}</span>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(codeString)}
                      className="hover:text-blue-300 transition-colors cursor-pointer text-[10px] sm:text-[11px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700"
                    >
                      Copy
                    </button>
                  </div>
                  <pre className="p-2.5 sm:p-3 overflow-x-auto text-[11px] sm:text-xs font-mono text-cyan-300 leading-normal scrollbar-thin">
                    <code>{codeString}</code>
                  </pre>
                </div>
              );
            }

            return (
              <code
                className="px-1.5 py-0.5 rounded bg-slate-100 text-blue-700 font-mono text-[11px] sm:text-xs border border-slate-200 break-all"
                {...props}
              >
                {children}
              </code>
            );
          },
          table({ children }) {
            return (
              <div className="my-2 sm:my-3 overflow-x-auto rounded-lg border border-slate-200 -mx-1 sm:mx-0">
                <table className="min-w-full divide-y divide-slate-200 text-left text-[11px] sm:text-xs">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="bg-slate-100 px-2.5 sm:px-3 py-1.5 font-semibold text-slate-800 whitespace-nowrap">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="px-2.5 sm:px-3 py-1.5 border-t border-slate-200 text-slate-700">
                {children}
              </td>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

