import { createAsyncThunk } from "@reduxjs/toolkit"
import { requestFileUploadUrls, type FileUploadMetadata } from "./index"

export const fetchFileUploadUrls = createAsyncThunk(
    "fileUploads/fetchUrls",
    (files: FileUploadMetadata[], {signal}) => requestFileUploadUrls(files, signal),
)
