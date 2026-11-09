import rehypeKatex from "rehype-katex"
import remarkMath from "remark-math"

import type { RehypePlugins, RemarkPlugins } from "@/markdown-plugins"

// Loaded on demand by message-markdown.tsx: KaTeX and the HTML parser rehype-katex needs are most
// of the widget's weight, and few answers contain maths. The KaTeX stylesheet stays in the main
// CSS (main.tsx), so only this JavaScript is deferred.

// `$...$` and `$$...$$` are the only maths delimiters, and remark-math owns them exclusively;
// `\[...\]` is used by the backend for citations and source attributions, so it must render as
// literal text.
export const mathRemarkPlugins: RemarkPlugins = [remarkMath]

export const mathRehypePlugins: RehypePlugins = [
  // maxSize caps user-visible dimensions: without it a response containing
  // \rule{500em}{500em} paints a screen-filling block on the farmer's phone.
  [rehypeKatex, { maxSize: 20 }],
]
