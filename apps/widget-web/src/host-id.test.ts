import { describe, expect, it } from "vitest"

import { resolveHostId } from "@/host-id"

function documentWithHost(hostId?: string): Document {
  return {
    querySelector: () => (hostId ? { content: hostId } : null),
  } as unknown as Document
}

describe("resolveHostId", () => {
  it("reads the production embed metadata", () => {
    expect(
      resolveHostId(documentWithHost("AMULAI-HOST-6c48b031"), "/ignored"),
    ).toBe("AMULAI-HOST-6c48b031")
  })

  it("reads the development route", () => {
    expect(
      resolveHostId(documentWithHost(), "/embed/AMULAI-HOST-6c48b031"),
    ).toBe("AMULAI-HOST-6c48b031")
  })

  it("rejects malformed host IDs", () => {
    expect(resolveHostId(documentWithHost(), "/embed/partner-a")).toBeNull()
  })
})
