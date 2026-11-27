import type { ChapterCreateFormSchema } from "./CreateChapterForm"
import type { ChapterUpdateFormSchema } from "./UpdateChapterInfoForm"
import type { ChapterUploadStatus } from "./useChapterUploads"

export type ChapterCreateSubmission = Omit<ChapterCreateFormSchema, "pages"> & {
    pages: {uuid: string, width: number, height: number}[]
}

export type ChapterUpdateSubmission = Omit<ChapterUpdateFormSchema, "pages"> & {
    pages: (
        {uuid: string, is_new: false} |
        (ChapterCreateSubmission["pages"][number] & {is_new: true})
    )[]
}

export function prepareChapterUpdate(data: ChapterUpdateFormSchema, statuses: Record<string, ChapterUploadStatus>) {
    const pages: ChapterUpdateSubmission["pages"] = []
    for (const page of data.pages) {
        if (!page.file) {
            pages.push({uuid: page.uuid, is_new: false})
            continue
        }
        const status = statuses[page.uuid]
        if (status?.state !== "ready" || !status.dimensions) return
        pages.push({uuid: page.uuid, is_new: true, ...status.dimensions})
    }
    return {...data, pages}
}

export function convertFormDataIntoJSON(data: ChapterCreateSubmission | ChapterUpdateSubmission) {
    return JSON.stringify({
        name: data.name.trim() || null,
        chapter: Number(data.chapter),
        privacy_id: Number(data.privacyId),
        extra_number: data.isExtra ? Number(data.extraNumber) : null,
        pages: data.pages,
    })
}
