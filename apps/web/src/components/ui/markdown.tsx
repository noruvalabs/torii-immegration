"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className = "" }: MarkdownProps) {
  return (
    <div className={`leading-relaxed ${className}`}>
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="mb-2 last:mb-0 list-disc pl-4 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 last:mb-0 list-decimal pl-4 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          code: ({ children }) => (
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="mb-2 last:mb-0 overflow-x-auto rounded bg-muted/60 p-2 font-mono text-[11px]">
              {children}
            </pre>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline hover:text-primary/80 font-medium"
            >
              {children}
            </a>
          ),
          h1: ({ children }) => <h1 className="text-sm font-bold mb-1.5 mt-2 first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xs font-bold mb-1 mt-2 first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="text-xs font-semibold mb-1 mt-1.5 first:mt-0">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/40 pl-2.5 my-1.5 text-muted-foreground italic">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
