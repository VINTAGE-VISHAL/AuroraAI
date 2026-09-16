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
    <div className="prose max-w-none text-slate-800 text-sm leading-relaxed tracking-wide">
      <ReactMarkdown
        remarkPlugins={markdownPlugins.remarkPlugins}
        rehypePlugins={markdownPlugins.rehypePlugins}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const codeString = String(children).replace(/\n$/, "");

            if (!inline && match) {
              return (
                <div className="relative my-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950 text-slate-100 shadow-md">
                  <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-slate-800 text-xs font-mono text-slate-400">
                    <span>{match[1]}</span>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(codeString)}
                      className="hover:text-blue-300 transition-colors cursor-pointer text-[11px]"
                    >
                      Copy
                    </button>
                  </div>
                  <pre className="p-3 overflow-x-auto text-xs font-mono text-cyan-300 leading-normal">
                    <code>{codeString}</code>
                  </pre>
                </div>
              );
            }

            return (
              <code
                className="px-1.5 py-0.5 rounded bg-slate-100 text-blue-700 font-mono text-[13px] border border-slate-200"
                {...props}
              >
                {children}
              </code>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="bg-slate-100 px-3 py-2 font-semibold text-slate-700">
                {children}
              </th>
            );
          },
          td({ children }) {
            return <td className="px-3 py-2 border-t border-slate-200 text-slate-700">{children}</td>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
