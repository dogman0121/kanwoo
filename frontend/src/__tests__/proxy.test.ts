/** @jest-environment node */

import { decodeJwt } from "jose"
import { NextRequest } from "next/server"
import { proxy } from "@/proxy"

jest.mock("jose", () => ({ decodeJwt: jest.fn() }))

const decodeJwtMock = jest.mocked(decodeJwt)
const authCookies = [
    "access_token_cookie=access",
    "refresh_token_cookie=refresh",
    "test_csrf_access=csrf",
    "test_csrf_refresh=refresh-csrf",
    "test_profile=42",
].join("; ")

function createRequest(pathname: string, cookies: string) {
    return new NextRequest(new URL(pathname, "https://kanwoo.test"), {
        headers: {
            Cookie: cookies,
            "X-CSRF-TOKEN": "csrf",
        },
    })
}

beforeEach(() => {
    jest.replaceProperty(process, "env", {
        ...process.env,
        NEXT_PUBLIC_CSRF_ACCESS_COOKIE_NAME: "test_csrf_access",
        NEXT_PUBLIC_CSRF_REFRESH_COOKIE_NAME: "test_csrf_refresh",
        AUTH_PROFILE_COOKIE_NAME: "test_profile",
    })
    decodeJwtMock.mockReset()
})

afterEach(() => jest.restoreAllMocks())

test.each(["/catalog", "/api/profiles/me"])(
    "drops auth cookies and the CSRF header on a JWT error for %s",
    async (pathname) => {
        decodeJwtMock.mockImplementation(() => {
            throw new Error("Invalid JWT")
        })
        const response = await proxy(createRequest(pathname, authCookies + "; theme=dark"))

        expect(response.headers.get("x-middleware-request-cookie")).toBe("theme=dark")
        expect(response.headers.get("x-middleware-request-x-csrf-token")).toBeNull()
        expect(response.headers.get("x-middleware-override-headers")?.split(",")).not.toContain("x-csrf-token")
        expect(response.headers.has("set-cookie")).toBe(false)
    },
)

test("drops the Cookie header when all cookies belong to the session", async () => {
    decodeJwtMock.mockImplementation(() => {
        throw new Error("Invalid JWT")
    })
    const response = await proxy(createRequest("/api/profiles/me", authCookies))

    expect(response.headers.get("x-middleware-request-cookie")).toBeNull()
    expect(response.headers.get("x-middleware-override-headers")?.split(",")).not.toContain("cookie")
})

test("forwards session cookies and the CSRF header for an unexpired token", async () => {
    decodeJwtMock.mockReturnValue({ exp: Math.floor(Date.now() / 1000) + 60 })
    const response = await proxy(createRequest("/api/profiles/me", authCookies))

    expect(response.headers.get("x-middleware-request-cookie")).toBe(authCookies)
    expect(response.headers.get("x-middleware-request-x-csrf-token")).toBe("csrf")
})
