import { renderToStaticMarkup } from "react-dom/server"
import ReactMarkdown from "react-markdown"
import { describe, expect, it } from "vitest"

import { chatRehypePlugins, chatRemarkPlugins } from "@/markdown-plugins"
import { repairMarkdownTables } from "@/markdown-tables"

// Ported from amul-ui's markdown-rendering.test.tsx so both chats are held to the same
// behaviour. Renders through the exact plugin configuration the widget uses; inputs marked
// "production" are taken verbatim from production chat.
function render(body: string): string {
  return renderToStaticMarkup(
    <ReactMarkdown remarkPlugins={chatRemarkPlugins} rehypePlugins={chatRehypePlugins}>
      {repairMarkdownTables(body)}
    </ReactMarkdown>,
  )
}

const isMath = (html: string) => html.includes('class="katex')

describe("assistant markdown rendering", () => {
  describe("maths renders", () => {
    it("renders production inline dollar maths", () => {
      const html = render("total fat is $15 \\times 4.8 = 720$ grams.")

      expect(isMath(html)).toBe(true)
      expect(html).not.toContain("$")
    })

    it("renders production percentage maths", () => {
      expect(isMath(render("ફેટ $2.6\\%$ છે."))).toBe(true)
    })

    it("renders block dollar maths as display maths", () => {
      expect(render("Formula:\n\n$$\n\\pi r^2\n$$\n")).toContain("katex-display")
    })
  })

  // The backend uses `\[...\]` for citations and source attributions, never for maths.
  describe("citations stay literal", () => {
    it.each([
      ["numeric markers", "પ્રજનન કરાવો. \\[1\\]\\[2\\]", "[1][2]"],
      ["document id", "વરસાદ પછી. \\[doc-c3c9fec0ddfb\\]", "[doc-c3c9fec0ddfb]"],
      [
        "source attribution",
        "Summary.\n\\[Source: Scientific herd nutrition guidelines\\]",
        "[Source: Scientific herd nutrition guidelines]",
      ],
    ])("renders %s as plain text", (_label, input, expected) => {
      const html = render(input)

      expect(isMath(html)).toBe(false)
      expect(html).toContain(expected)
    })

    it("does not swallow the prose between two citation markers", () => {
      const html = render(
        "પ્રજનન કરાવો. \\[1\\]\\[2\\] આ મહત્વનું છે અને દરરોજ આપો. \\[doc-56db97fcf363\\]",
      )

      expect(isMath(html)).toBe(false)
      expect(html).toContain("આ મહત્વનું છે અને દરરોજ આપો.")
    })
  })

  describe("code is never treated as maths", () => {
    it("keeps maths inside an inline code span literal", () => {
      const html = render("Use `$x^2$` in code.")

      expect(isMath(html)).toBe(false)
      expect(html).toContain("<code>$x^2$</code>")
    })

    it("keeps maths inside a fenced block literal", () => {
      expect(isMath(render("```\n$x^2$\n```"))).toBe(false)
    })
  })

  describe("surrounding markdown survives", () => {
    it("keeps a table intact when a cell contains maths", () => {
      const html = render("| A | B |\n|---|---|\n| Area | $\\pi r^2$ |\n| Milk | 5 L |")

      expect(html).toContain("<table ")
      expect((html.match(/<tr>/g) ?? []).length).toBe(3)
      expect(html).toContain("5 L")
      expect(isMath(html)).toBe(true)
    })

    it("keeps a list intact when an item contains maths", () => {
      const html = render("- Yield: $a+b$\n- Next bullet")

      expect((html.match(/<li>/g) ?? []).length).toBe(2)
      expect(html).toContain("Next bullet")
    })
  })

  // GFM rejects a table whose header and delimiter rows disagree on the column count, and the
  // whole table then renders as one paragraph of raw pipes.
  describe("tables with a stray pipe still render", () => {
    // production 2026-10-29, trace f5b578d9: the translator put a `|` inside "(Rs./Qtl)"
    const APMC_GU =
      "અહીં છે:\n\n| ચીજવસ્તુ | બજાર | જિલ્લો | મોડલ ભાવ (રૂ.| /ક્યુટીએલ) | રેન્જ (મિન - મેક્સ) |\n" +
      "| :--- | :--- | :--- | :--- | :--- |\n" +
      "| **ટમેટા** | હિંમતનગર (વેજ.માર્કેટ) | સાબરકાંઠા | 850 | 500 - 1000 |\n" +
      "| **લીંબુ** | હિંમતનગર (વેજ.માર્કેટ) | સાબરકાંઠા | 10300 | 10000 - 10500 |"

    it("renders the production Gujarati APMC table", () => {
      const html = render(APMC_GU)

      expect(html).toContain("<table ")
      expect((html.match(/<tr>/g) ?? []).length).toBe(3)
      expect((html.match(/<th[ >]/g) ?? []).length).toBe(5)
      expect(html).toContain("મોડલ ભાવ (રૂ. /ક્યુટીએલ)")
      expect(html).not.toContain("| :---")
    })

    it("re-joins a body cell split inside parentheses instead of dropping its tail", () => {
      expect(render("| Item | Price |\n|---|---|\n| Milk | 40 (Rs.| /L) |")).toContain(
        "40 (Rs. /L)",
      )
    })

    it("widens the delimiter row when the extra header cell is not a split", () => {
      const html = render("| A | B | C |\n|---|---|\n| 1 | 2 | 3 |")

      expect(html).toContain("<table ")
      expect(html).toMatch(/<td[^>]*>3<\/td>/)
    })

    it("leaves well-formed tables and fenced code byte-for-byte", () => {
      const table = "| A | B |\n|:-|-:|\n| x | y (z |"
      const fenced = "```\n| a | b | c |\n|---|---|\n```"

      expect(repairMarkdownTables(table)).toBe(table)
      expect(repairMarkdownTables(fenced)).toBe(fenced)
    })
  })

  describe("table layout annotations", () => {
    const cellAttrs = (html: string, text: string) =>
      html.match(new RegExp(`<t[dh]([^>]*)>${text}<`))?.[1] ?? ""

    it("counts columns and marks number and range columns numeric", () => {
      const html = render(
        "| Crop | Market | Price | Range |\n| :--- | :--- | :--- | :--- |\n" +
          "| Tomato | Himatnagar APMC | 850 | 500 - 1000 |\n| Onion | Deesa | ₹ 4,300 | 4000–4500 |",
      )

      expect(html).toContain('data-columns="4"')
      expect(cellAttrs(html, "850")).toContain("data-numeric")
      expect(cellAttrs(html, "500 - 1000")).toContain("data-numeric")
      expect(cellAttrs(html, "Price")).toContain("data-numeric")
      expect(cellAttrs(html, "Himatnagar APMC")).not.toContain("data-numeric")
      // the reflexive `:---` left alignment is dropped for numbers, kept for text
      expect(cellAttrs(html, "850")).not.toContain("text-align")
      expect(cellAttrs(html, "Tomato")).toContain("text-align:left")
    })

    it("treats Gujarati digits and percentages as numbers", () => {
      const html = render("| પશુ | દૂધ | ફેટ |\n|---|---|---|\n| ગાય | ૧૨ | 4.5% |")

      expect(cellAttrs(html, "૧૨")).toContain("data-numeric")
      expect(cellAttrs(html, "4.5%")).toContain("data-numeric")
    })

    it("keeps a column with any text out of numeric layout", () => {
      const html = render("| A | B |\n|---|---|\n| x | 12 |\n| y | not known |")

      expect(html).toContain('data-columns="2"')
      expect(cellAttrs(html, "12")).not.toContain("data-numeric")
    })
  })

  describe("hostile model output is contained", () => {
    it("clamps oversized KaTeX dimensions", () => {
      const html = render("Note $\\rule{500em}{500em}$ end.")

      const oversized = [...html.matchAll(/[a-z-]+:([0-9.]+)em/g)].filter(
        (match) => Number(match[1]) > 50,
      )
      expect(oversized).toHaveLength(0)
    })

    it("does not emit a link for \\href", () => {
      const html = render("Note $\\href{javascript:alert(1)}{click}$ end.")

      expect(html).not.toContain("<a ")
      expect(html).not.toContain("href=")
    })
  })
})
