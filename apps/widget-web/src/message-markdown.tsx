import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"

// The advisory API answers in markdown (paragraphs, bullet lists, bold labels, tables).
// Raw HTML stays off: react-markdown escapes it unless rehype-raw is added.
const remarkPlugins = [remarkGfm]

const components: Components = {
  // Following a link inside the iframe would replace the conversation.
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
}

export function MessageMarkdown({ text }: { text: string }) {
  return (
    <div className="widget-markdown">
      <ReactMarkdown remarkPlugins={remarkPlugins} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  )
}
