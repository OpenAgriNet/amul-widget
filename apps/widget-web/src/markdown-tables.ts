import type { Element, ElementContent, Root, RootContent } from "hast"

// Ported from amul-ui (chat-screen/components/bubbles/markdown-tables.ts) so the widget lays out
// the advisory API's tables the same way the main chat does.

/**
 * Repairs GFM pipe tables whose rows were split by a stray `|`.
 *
 * GFM only accepts a table when the header row has exactly as many cells as the delimiter row;
 * otherwise every line falls back into one paragraph and the farmer sees raw `| ... |` text.
 * Translation sometimes inserts a pipe inside a cell — production Gujarati turned
 * "Modal Price (Rs./Qtl)" into `મોડલ ભાવ (રૂ.| /ક્યુટીએલ)` — so a header gains a column the
 * delimiter row doesn't have.
 *
 * Only tables that GFM would reject (header) or truncate (body rows with excess cells) are
 * touched; every other line is returned byte-for-byte, and fenced code is skipped.
 */

const FENCE = /^\s{0,3}(```|~~~)/
const DELIMITER_ROW = /^\s{0,3}\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/
const UNESCAPED_PIPE = /(?<!\\)\|/

function splitRow(line: string): string[] {
  const cells = line.trim().split(UNESCAPED_PIPE).map((cell) => cell.trim())
  if (cells[0] === "") cells.shift()
  if (cells[cells.length - 1] === "") cells.pop()
  return cells
}

const joinRow = (cells: string[]) => `| ${cells.join(" | ")} |`

const count = (text: string, char: string) => text.split(char).length - 1

/** Re-joins cells that were split inside parentheses, while the row has more cells than columns. */
function mergeSplitCells(cells: string[], columns: number): string[] {
  let excess = cells.length - columns
  const merged: string[] = []
  for (const cell of cells) {
    const prev = merged[merged.length - 1]
    if (excess > 0 && prev !== undefined && count(prev, "(") > count(prev, ")")) {
      merged[merged.length - 1] = `${prev} ${cell}`
      excess--
      continue
    }
    merged.push(cell)
  }
  return merged
}

export function repairMarkdownTables(markdown: string): string {
  if (!markdown.includes("|")) return markdown

  const lines = markdown.split("\n")
  let inFence = false

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ""
    const prevLine = lines[i - 1] ?? ""
    if (FENCE.test(line)) {
      inFence = !inFence
      continue
    }
    if (inFence || !line.includes("|") || !prevLine.includes("|") || !DELIMITER_ROW.test(line)) {
      continue
    }

    const originalHeader = splitRow(prevLine)
    const delimiter = splitRow(line)
    const delimiterCount = delimiter.length
    let header = originalHeader
    let columns = delimiterCount

    if (header.length > columns) header = mergeSplitCells(header, columns)
    if (header.length < columns) {
      header = [...header, ...Array<string>(columns - header.length).fill("")]
    }
    if (header.length > columns) {
      delimiter.push(...Array<string>(header.length - columns).fill("---"))
      columns = header.length
    }
    if (header.length !== originalHeader.length || delimiter.length !== delimiterCount) {
      lines[i - 1] = joinRow(header)
      lines[i] = joinRow(delimiter)
    }

    for (let j = i + 1; j < lines.length; j++) {
      const row = lines[j] ?? ""
      if (!row.includes("|") || row.trim() === "") break
      const cells = splitRow(row)
      if (cells.length <= columns) continue
      const merged = mergeSplitCells(cells, columns)
      if (merged.length < cells.length) lines[j] = joinRow(merged)
    }
  }

  return lines.join("\n")
}

// A cell is numeric when it is a number or a range, optionally with a currency sign or percent:
// "850", "₹ 1,200", "500 - 1000", "4.8%". Gujarati and Devanagari digits count.
const DIGITS = "\\d\\u0AE6-\\u0AEF\\u0966-\\u096F"
const NUMBER = `[-+]?[₹$]?\\s*[${DIGITS}][${DIGITS}.,]*`
const NUMERIC_CELL = new RegExp(`^${NUMBER}(\\s*[-–—]\\s*${NUMBER})?\\s*%?$`)

const isElement = (node: ElementContent | RootContent): node is Element => node.type === "element"

function textOf(node: ElementContent): string {
  if (node.type === "text") return node.value
  return isElement(node) ? node.children.map(textOf).join("") : ""
}

function rowsOf(table: Element): Element[] {
  return table.children
    .filter(isElement)
    .flatMap((section) =>
      section.tagName === "tr" ? [section] : section.children.filter(isElement),
    )
    .filter((row) => row.tagName === "tr")
}

/**
 * Annotates GFM tables so the bubble can lay them out: `data-columns` on the table, and
 * `data-numeric` on every cell of a column whose body cells are all numbers or ranges.
 */
function annotateTable(table: Element) {
  const rows = rowsOf(table).map((row) => row.children.filter(isElement))
  const columns = Math.max(0, ...rows.map((cells) => cells.length))
  table.properties.dataColumns = columns

  for (let col = 0; col < columns; col++) {
    const body = rows.flatMap((cells) =>
      cells.filter((cell, i) => i === col && cell.tagName === "td"),
    )
    const values = body.map((cell) => textOf(cell).trim()).filter(Boolean)
    if (!values.length || !values.every((value) => NUMERIC_CELL.test(value))) continue
    for (const cells of rows) {
      const cell = cells[col]
      if (!cell) continue
      cell.properties.dataNumeric = true
      // Models write `:---` on every column by reflex; numbers still read best right-aligned.
      if (cell.properties.align === "left") delete cell.properties.align
    }
  }
}

function visitTables(node: Root | Element) {
  for (const child of node.children) {
    if (!isElement(child)) continue
    if (child.tagName === "table") annotateTable(child)
    else visitTables(child)
  }
}

export const rehypeChatTables = () => (tree: Root) => visitTables(tree)
