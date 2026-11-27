import { clientFetch } from "@/lib/fetch/client-fetch.util"

export type FileUploadMetadata = {
    uuid: string
    file_type: string
    name: string
    mimetype: string
    file_size: number
}

export type FileUploadUrl = {
    uuid: string
    presigned_url: string
}

export async function requestFileUploadUrls(files: FileUploadMetadata[], signal?: AbortSignal) {
    const response = await clientFetch.post<FileUploadUrl[]>("/uploads", {
        body: JSON.stringify(files),
        signal,
    }, {use_json: true})
    return response.data
}
