import type { Options } from "react-markdown"
import rehypeKatex from "rehype-katex"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"

import { rehypeChatTables } from "@/markdown-tables"

type RemarkPlugins = NonNullable<Options["remarkPlugins"]>
type RehypePlugins = NonNullable<Options["rehypePlugins"]>

/**
 * Markdown plugin configuration for assistant answers, matching amul-ui's chat bubble.
 *
 * Answers are passed to react-markdown untouched — there is deliberately no pre-parse
 * normalisation of maths delimiters. `$...$` and `$$...$$` are the only maths delimiters, and
 * remark-math owns them exclusively; `\[...\]` is used by the backend for citations and source
 * attributions, so it must render as literal text.
 *
 * Exported so the rendering tests exercise exactly the configuration the widget uses.
 */
export const chatRemarkPlugins: RemarkPlugins = [remarkGfm, remarkMath]

export const chatRehypePlugins: RehypePlugins = [
  // before KaTeX, so numeric-column detection reads the source text of maths cells
  rehypeChatTables,
  // maxSize caps user-visible dimensions: without it a response containing
  // \rule{500em}{500em} paints a screen-filling block on the farmer's phone.
  [rehypeKatex, { maxSize: 20 }],
]
