import { useCallback, useRef } from "react"
import { v4 } from "uuid"

export function useIdempotency() {
    const attempt = useRef<{json: string, key: string} | null>(null)

    const getKey = useCallback((json: string) => {
        if (attempt.current?.json !== json) {
            attempt.current = {json, key: v4()}
        }
        return attempt.current.key
    }, [])

    const reset = useCallback(() => {
        attempt.current = null
    }, [])

    return {getKey, reset}
}
