import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';

const MathRenderer = ({ content }) => {
  return (
    <div className="math-content max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{
          h2: ({ children }) => (
            <h2 className="math-heading-2 text-lg font-bold mt-4 mb-2 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="math-heading-3 text-base font-semibold mt-3 mb-1">
              {children}
            </h3>
          ),
          strong: ({ children }) => (
            <strong className="math-strong font-semibold">
              {children}
            </strong>
          ),
          p: ({ children }) => (
            <p className="math-paragraph mb-2 leading-relaxed">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="math-list list-disc list-inside mb-2">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="math-list list-decimal list-inside mb-2">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="math-list-item mb-1">
              {children}
            </li>
          ),
          code: ({ children }) => (
            <code className="math-code px-1.5 py-0.5 rounded text-sm">
              {children}
            </code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="math-blockquote border-l-4 pl-4 my-2 italic">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="math-hr my-3" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MathRenderer;

