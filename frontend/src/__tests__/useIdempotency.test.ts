import { renderHook } from "@testing-library/react"
import { useIdempotency } from "@/lib/use-idempotency.hook"

jest.mock("uuid", () => ({v4: jest.requireActual("node:crypto").randomUUID}))

test("reuses the key for the same request JSON across renders and changes it for new JSON", () => {
    const {result, rerender} = renderHook(() => useIdempotency())
    const body = JSON.stringify({chapter: 1})
    const originalKey = result.current.getKey(body)

    rerender()
    expect(result.current.getKey(body)).toBe(originalKey)

    const nextBody = JSON.stringify({chapter: 2})
    const nextKey = result.current.getKey(nextBody)
    expect(nextKey).not.toBe(originalKey)
    expect(result.current.getKey(nextBody)).toBe(nextKey)
})

test("starts a new attempt for the same JSON after reset", () => {
    const {result} = renderHook(() => useIdempotency())
    const body = JSON.stringify({chapter: 1})
    const originalKey = result.current.getKey(body)

    result.current.reset()

    expect(result.current.getKey(body)).not.toBe(originalKey)
})
