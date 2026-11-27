import { act, renderHook, waitFor } from "@testing-library/react"
import { configureStore } from "@reduxjs/toolkit"
import { createElement, type PropsWithChildren } from "react"
import { Provider } from "react-redux"
import type { EditFile } from "@/components/edit/MultipleFilesInput"
import { requestFileUploadUrls } from "@/lib/file-uploads"
import { useChapterUploads } from "@/features/studio/forms/useChapterUploads"

jest.mock("@/lib/file-uploads", () => ({
    requestFileUploadUrls: jest.fn(),
}))

const store = configureStore({reducer: (state = {}) => state})
const wrapper = ({children}: PropsWithChildren) => createElement(Provider, {store, children})

test("existing pages are idle and can be saved without requesting an upload", () => {
    const pages = [
        {uuid: "first", name: "page.png", previewLink: "/first.png"},
        {uuid: "second", name: "page.png", previewLink: "/second.png"},
    ]
    const {result} = renderHook(() => useChapterUploads(pages), {wrapper})

    expect(result.current.ready).toBe(true)
    expect(result.current.statuses).toEqual({first: {state: "idle"}, second: {state: "idle"}})
    expect(requestFileUploadUrls).not.toHaveBeenCalled()
})

test("uploads three pages at a time and retries only the failed page with its original UUID", async () => {
    const pages: EditFile[] = Array.from({length: 4}, (_, index) => ({
        uuid: `file-${index}`,
        name: "same-name.png",
        previewLink: `blob:page-${index}`,
        file: new File(["image"], "same-name.png", {type: "image/png"}),
    }))
    const signedUrls = jest.mocked(requestFileUploadUrls)
    signedUrls.mockImplementation(async files => files.map(({uuid}) => ({
        uuid, presigned_url: "https://storage.example",
    })))
    const requests: XMLHttpRequest[] = []
    const send = jest.spyOn(XMLHttpRequest.prototype, "send").mockImplementation(function (
        this: XMLHttpRequest,
    ) {
        requests.push(this)
    })
    const createBitmap = globalThis.createImageBitmap
    globalThis.createImageBitmap = jest.fn().mockResolvedValue({width: 8, height: 12, close: jest.fn()})
    const open = jest.spyOn(XMLHttpRequest.prototype, "open")
    const revokeObjectURL = URL.revokeObjectURL
    URL.revokeObjectURL = jest.fn()

    const {result, rerender, unmount} = renderHook(useChapterUploads, {wrapper, initialProps: pages})
    const complete = (index: number, status: number) => {
        Object.defineProperty(requests[index], "status", {value: status})
        requests[index].dispatchEvent(new Event("load"))
        requests[index].dispatchEvent(new Event("loadend"))
    }

    try {
        await waitFor(() => expect(requests).toHaveLength(3))
        expect(result.current.statuses[pages[3].uuid]).toBeUndefined()
        expect(open).toHaveBeenCalledWith("PUT", "https://storage.example")
        expect(send).toHaveBeenCalledWith(pages[0].file)
        act(() => requests[0].upload.dispatchEvent(new ProgressEvent("progress", {
            lengthComputable: true, loaded: 72, total: 100,
        })))
        expect(result.current.statuses[pages[0].uuid]).toEqual({state: "uploading", progress: 72})
        expect(signedUrls).toHaveBeenCalledTimes(1)

        await act(async () => {
            complete(0, 204)
            complete(1, 403)
            complete(2, 204)
        })
        await waitFor(() => expect(requests).toHaveLength(4))
        expect(result.current.statuses[pages[1].uuid]).toEqual({state: "error"})
        expect(result.current.ready).toBe(false)

        act(() => result.current.retry(pages[1].uuid))
        await waitFor(() => expect(requests).toHaveLength(5))
        expect(signedUrls.mock.calls.map(([files]) => files.map(({uuid}) => uuid))).toEqual([
            pages.slice(0, 3).map(({uuid}) => uuid), [pages[3].uuid], [pages[1].uuid],
        ])

        await act(async () => {
            complete(3, 204)
            complete(4, 412)
        })
        expect(result.current.ready).toBe(true)
        expect(result.current.statuses[pages[1].uuid]).toEqual({
            state: "ready", dimensions: {width: 8, height: 12},
        })

        const removed = {...pages[0], uuid: "removed", previewLink: "blob:removed"}
        const invalid = {
            ...removed,
            uuid: "invalid",
            previewLink: "blob:invalid",
            file: new File(["image"], "page.gif", {type: "image/gif"}),
        }
        rerender([...pages, invalid, removed])
        await waitFor(() => expect(requests).toHaveLength(6))
        expect(result.current.statuses.invalid).toEqual({state: "error"})
        expect(signedUrls.mock.lastCall?.[0].map(({uuid}) => uuid)).toEqual([removed.uuid])
        const abort = jest.spyOn(requests[5], "abort")
        rerender(pages)
        expect(abort).toHaveBeenCalledTimes(1)
        expect(URL.revokeObjectURL).toHaveBeenCalledWith(removed.previewLink)
        expect(result.current.ready).toBe(true)
        expect(result.current.statuses[removed.uuid]).toBeUndefined()
    } finally {
        unmount()
        send.mockRestore()
        open.mockRestore()
        globalThis.createImageBitmap = createBitmap
        URL.revokeObjectURL = revokeObjectURL
    }
})
