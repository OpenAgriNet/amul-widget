import { describe, expect, it } from "vitest"

import { parseSseBlock } from "@/api"

describe("parseSseBlock", () => {
  it("parses a typed message delta", () => {
    expect(parseSseBlock('event: message.delta\ndata: {"text":"hello"}')).toEqual({
      event: "message.delta",
      data: { text: "hello" },
    })
  })

  it("ignores incomplete blocks", () => {
    expect(parseSseBlock("data: {}")).toBeNull()
  })
})
