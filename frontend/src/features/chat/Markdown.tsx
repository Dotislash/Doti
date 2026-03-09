import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import type { Components } from "react-markdown";

const components: Components = {
  pre({ children }) {
    return (
      <pre className="my-2 overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] p-3 text-[13px] leading-6">
        {children}
      </pre>
    );
  },
  code({ className, children, ...props }) {
    const isBlock = className?.startsWith("language-");
    if (isBlock) {
      return (
        <code className={`${className ?? ""} text-[var(--text-primary)]`} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-[rgba(95,145,255,0.15)] px-1.5 py-0.5 text-[13px] text-[var(--accent)]" {...props}>
        {children}
      </code>
    );
  },
  p({ children }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
  },
  ul({ children }) {
    return <ul className="mb-2 list-disc pl-5 last:mb-0">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="mb-2 list-decimal pl-5 last:mb-0">{children}</ol>;
  },
  li({ children }) {
    return <li className="mb-0.5">{children}</li>;
  },
  h1({ children }) {
    return <h1 className="mb-2 mt-3 text-lg font-semibold first:mt-0">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="mb-2 mt-3 text-base font-semibold first:mt-0">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="mb-1.5 mt-2.5 text-sm font-semibold first:mt-0">{children}</h3>;
  },
  blockquote({ children }) {
    return (
      <blockquote className="my-2 border-l-2 border-[var(--accent)] pl-3 text-[var(--text-secondary)]">
        {children}
      </blockquote>
    );
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] underline decoration-[var(--accent)]/40 hover:decoration-[var(--accent)]">
        {children}
      </a>
    );
  },
  table({ children }) {
    return (
      <div className="my-2 overflow-x-auto">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return <th className="border border-[var(--border)] bg-[var(--bg-tertiary)] px-3 py-1.5 text-left font-medium">{children}</th>;
  },
  td({ children }) {
    return <td className="border border-[var(--border)] px-3 py-1.5">{children}</td>;
  },
  hr() {
    return <hr className="my-3 border-[var(--border)]" />;
  },
};

type MarkdownProps = {
  content: string;
};

export function Markdown({ content }: MarkdownProps) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={components}>
      {content}
    </ReactMarkdown>
  );
}
