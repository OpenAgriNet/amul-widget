import ReactMarkdown, { type Components } from "react-markdown"

import { ChatTable, ChatTableCell, ChatTableHeaderCell } from "@/chat-table"
import { chatRehypePlugins, chatRemarkPlugins } from "@/markdown-plugins"
import { repairMarkdownTables } from "@/markdown-tables"

// Element styling mirrors amul-ui's CardBubble, so an answer reads the same in the widget as in
// the main chat. Raw HTML stays off: react-markdown escapes it unless rehype-raw is added.
const components: Components = {
  p: ({ node: _node, ...props }) => <p className="mb-1.5 leading-snug last:mb-0" {...props} />,
  ol: ({ node: _node, ...props }) => (
    <ol className="my-1.5 list-decimal pl-6 [&>li]:mb-0.5 [&>li:last-child]:mb-0" {...props} />
  ),
  ul: ({ node: _node, ...props }) => (
    <ul className="my-1.5 list-disc pl-6 [&>li]:mb-0.5 [&>li:last-child]:mb-0" {...props} />
  ),
  li: ({ node: _node, ...props }) => <li className="pl-1" {...props} />,
  strong: ({ node: _node, ...props }) => (
    <strong className="font-semibold text-foreground/90" {...props} />
  ),
  // Following a link inside the iframe would replace the conversation.
  a: ({ node: _node, ...props }) => (
    <a
      {...props}
      className="text-primary underline underline-offset-2"
      target="_blank"
      rel="noopener noreferrer"
    />
  ),
  table: ChatTable,
  tr: ({ node: _node, ...props }) => <tr className="border-b last:border-b-0" {...props} />,
  th: ChatTableHeaderCell,
  td: ChatTableCell,
  h1: ({ node: _node, ...props }) => (
    <p className="mt-2 mb-1.5 text-base leading-snug font-bold first:mt-0" {...props} />
  ),
  h2: ({ node: _node, ...props }) => (
    <p className="mt-2 mb-1.5 leading-snug font-bold first:mt-0" {...props} />
  ),
  h3: ({ node: _node, ...props }) => (
    <p className="mt-2 mb-1 leading-snug font-semibold first:mt-0" {...props} />
  ),
  h4: ({ node: _node, ...props }) => (
    <p className="mt-1.5 mb-1 leading-snug font-semibold first:mt-0" {...props} />
  ),
  h5: ({ node: _node, ...props }) => (
    <p className="mt-1.5 mb-1 leading-snug font-semibold first:mt-0" {...props} />
  ),
  h6: ({ node: _node, ...props }) => (
    <p className="mt-1.5 mb-1 leading-snug font-semibold first:mt-0" {...props} />
  ),
  hr: ({ node: _node, ...props }) => <hr className="my-3 border-t" {...props} />,
}

export function MessageMarkdown({ text }: { text: string }) {
  return (
    <div className="leading-snug break-words">
      <ReactMarkdown
        remarkPlugins={chatRemarkPlugins}
        rehypePlugins={chatRehypePlugins}
        components={components}
      >
        {repairMarkdownTables(text)}
      </ReactMarkdown>
    </div>
  )
}
