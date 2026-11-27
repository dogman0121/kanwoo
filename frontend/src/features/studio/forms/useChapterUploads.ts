import { useEffect, useRef, useState } from "react"
import type { EditFile, UploadStatus } from "@/components/edit/MultipleFilesInput"
import type { FileUploadUrl } from "@/lib/file-uploads"
import { fetchFileUploadUrls } from "@/lib/file-uploads/requestFileUploadUrls.thunk"
import { useAppDispatch } from "@/lib/state/hooks"

export type ChapterUploadStatus = UploadStatus & {dimensions?: {width: number, height: number}}

const MAX_PARALLEL_UPLOADS = 3
const MAX_FILE_SIZE = 20 * 1024 * 1024
const ALLOWED_FILE_TYPES = new Set(["image/jpeg", "image/png"])

function sendToStorage(
    upload: FileUploadUrl,
    file: File,
    signal: AbortSignal,
    onProgress: (progress: number) => void,
) {
    return new Promise<void>((resolve, reject) => {
        signal.throwIfAborted()
        const xhr = new XMLHttpRequest()
        xhr.open("PUT", upload.presigned_url)
        xhr.setRequestHeader("Content-Type", file.type)
        xhr.setRequestHeader("If-None-Match", "*")
        xhr.timeout = 120_000
        const abort = () => xhr.abort()
        signal.addEventListener("abort", abort, {once: true})
        xhr.onloadend = () => signal.removeEventListener("abort", abort)
        xhr.onload = () => {
            if ((xhr.status >= 200 && xhr.status < 300) || xhr.status === 412) resolve()
            else reject(new Error("Object storage rejected the upload"))
        }
        xhr.onerror = xhr.ontimeout = xhr.onabort = () => reject(new Error("Upload interrupted"))
        xhr.upload.onprogress = event => {
            if (event.lengthComputable) {
                onProgress(Math.min(99, Math.floor(event.loaded / event.total * 100)))
            }
        }

        xhr.send(file)
    })
}

const EMPTY_PAGES: EditFile[] = []

export function useChapterUploads(pages = EMPTY_PAGES) {
    const dispatch = useAppDispatch()
    const [statuses, setStatuses] = useState<Record<string, ChapterUploadStatus>>({})
    const [queueVersion, setQueueVersion] = useState(0)
    const finished = useRef(new Set<string>())
    const active = useRef(new Map<string, AbortController>())
    const previews = useRef(new Map<string, string>())

    useEffect(() => {
        const controllers = active.current
        const links = previews.current
        return () => {
            controllers.forEach(controller => controller.abort())
            controllers.clear()
            links.forEach(link => URL.revokeObjectURL(link))
            links.clear()
        }
    }, [])

    useEffect(() => {
        const present = new Set(pages.flatMap(page => page.file ? [page.uuid] : []))
        const removed: string[] = []
        for (const [uuid, link] of previews.current) {
            if (!present.has(uuid)) {
                active.current.get(uuid)?.abort()
                active.current.delete(uuid)
                previews.current.delete(uuid)
                finished.current.delete(uuid)
                URL.revokeObjectURL(link)
                removed.push(uuid)
            }
        }
        if (removed.length) {
            setStatuses(current => {
                const next = {...current}
                for (const uuid of removed) delete next[uuid]
                return next
            })
        }

        const batch: {uuid: string, file: File, controller: AbortController}[] = []
        for (const page of pages) {
            const {uuid, file} = page
            if (!file) continue
            previews.current.set(uuid, page.previewLink)
            if (active.current.size >= MAX_PARALLEL_UPLOADS) continue
            if (active.current.has(uuid) || finished.current.has(uuid)) continue

            const controller = new AbortController()
            active.current.set(uuid, controller)
            batch.push({uuid, file, controller})
        }

        if (!batch.length) return
        const batchController = new AbortController()
        const pending = new Set(batch.map(({controller}) => controller))
        const cancelBatchIfEmpty = () => {
            if ([...pending].every(controller => controller.signal.aborted)) batchController.abort()
        }

        const prepared = batch.map(async ({file, controller}) => {
            controller.signal.addEventListener("abort", cancelBatchIfEmpty, {once: true})
            if (!file.size || file.size > MAX_FILE_SIZE) throw new Error("Invalid file size")
            if (!ALLOWED_FILE_TYPES.has(file.type) || !file.name || [...file.name].length > 255) {
                throw new Error("Invalid file metadata")
            }
            const bitmap = await createImageBitmap(file)
            const dimensions = {width: bitmap.width, height: bitmap.height}
            bitmap.close()
            return dimensions
        })

        const signedUrls = Promise.allSettled(prepared).then(results => {
            const metadata = batch.flatMap(({uuid, file, controller}, index) => {
                if (results[index].status === "rejected" || controller.signal.aborted) return []
                return [{
                    uuid,
                    file_type: "chapter_page",
                    mimetype: file.type,
                    name: file.name,
                    file_size: file.size,
                }]
            })
            return metadata.length
                ? dispatch(fetchFileUploadUrls(metadata, {signal: batchController.signal})).unwrap()
                : []
        })

        batch.forEach(({uuid, file, controller}, index) => {
            const updateStatus = (status: ChapterUploadStatus) => {
                if (controller.signal.aborted) return
                setStatuses(current => {
                    const previous = current[uuid]
                    if (status.state === "uploading" &&
                        previous?.state === "uploading" && previous.progress === status.progress) {
                        return current
                    }
                    return {...current, [uuid]: status}
                })
            }

            const uploadPage = async () => {
                try {
                    updateStatus({state: "uploading", progress: 0})
                    const [links, dimensions] = await Promise.all([signedUrls, prepared[index]])
                    controller.signal.throwIfAborted()
                    const upload = links.find(link => link.uuid === uuid)
                    if (!upload) throw new Error("Missing signed chapter upload")
                    await sendToStorage(upload, file, controller.signal, progress => {
                        updateStatus({state: "uploading", progress})
                    })
                    updateStatus({state: "ready", dimensions})
                } catch {
                    updateStatus({state: "error"})
                } finally {
                    controller.signal.removeEventListener("abort", cancelBatchIfEmpty)
                    pending.delete(controller)
                    if (active.current.get(uuid) === controller) {
                        active.current.delete(uuid)
                        if (!controller.signal.aborted) finished.current.add(uuid)
                        setQueueVersion(version => version + 1)
                    }
                }
            }
            void uploadPage()
        })
    }, [dispatch, pages, queueVersion])

    const pageStatuses: Record<string, ChapterUploadStatus> = {}
    for (const page of pages) {
        if (!page.file) pageStatuses[page.uuid] = {state: "idle"}
        else if (statuses[page.uuid]) pageStatuses[page.uuid] = statuses[page.uuid]
    }

    return {
        statuses: pageStatuses,
        retry: (uuid: string) => {
            if (statuses[uuid]?.state !== "error" || !finished.current.delete(uuid)) return
            setStatuses(current => ({...current, [uuid]: {state: "queued"}}))
            setQueueVersion(version => version + 1)
        },
        ready: pages.length > 0 && pages.every(page => {
            const state = pageStatuses[page.uuid]?.state
            return state === "idle" || state === "ready"
        }),
    }
}
