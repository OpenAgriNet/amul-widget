import type { Options } from "react-markdown"
import remarkGfm from "remark-gfm"

import { rehypeChatTables } from "@/markdown-tables"

export type RemarkPlugins = NonNullable<Options["remarkPlugins"]>
export type RehypePlugins = NonNullable<Options["rehypePlugins"]>

/**
 * Markdown plugin configuration for assistant answers, matching amul-ui's chat bubble. The maths
 * plugins live in `markdown-math.ts` and are appended once that chunk has loaded.
 *
 * Answers are passed to react-markdown untouched — there is deliberately no pre-parse
 * normalisation of maths delimiters.
 *
 * Exported so the rendering tests exercise exactly the configuration the widget uses.
 */
export const chatRemarkPlugins: RemarkPlugins = [remarkGfm]

// Runs before KaTeX, so numeric-column detection reads the source text of maths cells.
export const chatRehypePlugins: RehypePlugins = [rehypeChatTables]

/** Only answers with a `$` can hold maths, so only they load the maths chunk. */
export const mayContainMath = (text: string) => text.includes("$")
