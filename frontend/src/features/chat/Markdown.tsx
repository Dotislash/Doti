import { useCallback, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import type { Components } from "react-markdown";

/* ── Copy button for code blocks ── */
function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const copy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);

  return (
    <button
      onClick={copy}
      className="absolute right-3 top-3 rounded-full bg-secondary/80 backdrop-blur px-3 py-1 text-[11px] font-medium text-secondary-foreground opacity-0 transition-all hover:bg-secondary hover:shadow-sm group-hover:opacity-100"
    >
      {copied ? "copied!" : "copy"}
    </button>
  );
}

function extractText(node: React.ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (!node) return "";
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (typeof node === "object" && node !== null && "props" in node) {
    const el = node as { props: { children?: React.ReactNode } };
    return extractText(el.props.children);
  }
  return "";
}

const components: Components = {
  pre({ children }) {
    const text = extractText(children);
    return (
      <pre className="group relative my-4 overflow-x-auto rounded-3xl border border-border/50 bg-secondary/30 p-5 text-[13px] leading-relaxed shadow-inner-pebble">
        <CopyBtn text={text} />
        {children}
      </pre>
    );
  },
  code({ className, children, ...props }) {
    const isBlock = className?.startsWith("language-");
    if (isBlock) {
      const lang = className?.replace("language-", "") ?? "";
      return (
        <>
          {lang && (
            <span className="absolute left-5 top-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 select-none">
              {lang}
            </span>
          )}
          <code className={`${className ?? ""} block ${lang ? "pt-7" : ""} font-mono text-foreground`} {...props}>
            {children}
          </code>
        </>
      );
    }
    return (
      <code className="rounded-md bg-primary/10 px-1.5 py-0.5 font-mono text-[13px] font-medium text-primary" {...props}>
        {children}
      </code>
    );
  },
  p({ children }) {
    return <p className="mb-2.5 last:mb-0">{children}</p>;
  },
  ul({ children }) {
    return <ul className="mb-2.5 list-disc pl-5 last:mb-0">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="mb-2.5 list-decimal pl-5 last:mb-0">{children}</ol>;
  },
  li({ children }) {
    return <li className="mb-0.5">{children}</li>;
  },
  h1({ children }) {
    return <h1 className="mb-4 mt-6 text-2xl font-semibold tracking-tight first:mt-0">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="mb-3 mt-5 text-xl font-semibold tracking-tight first:mt-0">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="mb-2.5 mt-4 text-lg font-medium tracking-tight first:mt-0">{children}</h3>;
  },
  blockquote({ children }) {
    return (
      <blockquote className="my-4 border-l-4 border-primary/40 bg-primary/5 py-3 pl-5 pr-4 text-muted-foreground rounded-r-2xl">
        {children}
      </blockquote>
    );
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary font-medium underline decoration-primary/30 underline-offset-4 transition-all hover:decoration-primary">
        {children}
      </a>
    );
  },
  table({ children }) {
    return (
      <div className="my-5 overflow-x-auto rounded-2xl border border-border shadow-sm">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return <th className="border-b border-border bg-secondary/50 px-4 py-3 text-left font-semibold text-foreground">{children}</th>;
  },
  td({ children }) {
    return <td className="border-b border-border/50 px-4 py-3 text-muted-foreground last:border-0">{children}</td>;
  },
  hr() {
    return <hr className="my-6 border-border" />;
  },
};

type MarkdownProps = { content: string };

export function Markdown({ content }: MarkdownProps) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={components}>
      {content}
    </ReactMarkdown>
  );
}
