import { describe, expect, it } from "vitest"

import { assistantDisplayText } from "@/chat-wire"

const artifactFrame = (payload = "eyJ2ZXJzaW9uIjoxLCJhcnRpZmFjdHMiOltdfQ==") =>
  `\n__CHAT_ARTIFACTS__${payload}__END_CHAT_ARTIFACTS__\n`

describe("assistantDisplayText", () => {
  it("returns plain answers unchanged", () => {
    const answer = "* **સંતુલિત ચારો:** પેલેટ ચારો આપો.\n\n| A | B |\n|---|---|\n| 1 | 2 |"

    expect(assistantDisplayText(answer)).toBe(answer)
  })

  it("cuts an artifact frame out of the text", () => {
    expect(assistantDisplayText(`Your card is ready.${artifactFrame()}`)).toBe("Your card is ready.")
  })

  it("keeps the closing markers of an answer that ends in bold or italics", () => {
    expect(assistantDisplayText("Give **dry fodder** and __green fodder__")).toBe(
      "Give **dry fodder** and __green fodder__",
    )
    expect(assistantDisplayText("Keep the shed _clean_")).toBe("Keep the shed _clean_")
  })

  it("holds back a frame whose end marker has not arrived", () => {
    expect(assistantDisplayText("Your card is ready.\n__CHAT_ARTIFACTS__eyJ2ZX")).toBe(
      "Your card is ready.",
    )
  })

  it("holds back a start marker split across chunks", () => {
    expect(assistantDisplayText("Your card is ready.\n__CHAT_ART")).toBe("Your card is ready.")
  })

  it("strips the milk-collection guardrail prefix", () => {
    expect(
      assistantDisplayText("Farmer milk collection details fetched successfully:\n\n| A |"),
    ).toBe("| A |")
  })
})
