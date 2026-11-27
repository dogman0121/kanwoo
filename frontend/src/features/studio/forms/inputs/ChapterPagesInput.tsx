import { Box } from "@mui/material"
import EditLabel from "@/components/edit/Label"
import EditMultipleFilesInput, { type EditFile } from "@/components/edit/MultipleFilesInput"
import type { useChapterUploads } from "../useChapterUploads"

export default function ChapterPagesInput({value, onChange, uploads}: {
    value: EditFile[]
    onChange: (pages: EditFile[]) => void
    uploads: ReturnType<typeof useChapterUploads>
}) {
    return (
        <Box>
            <EditLabel>Страницы</EditLabel>
            <EditMultipleFilesInput
                value={value}
                onChange={onChange}
                uploadStatuses={uploads.statuses}
                onRetryUpload={uploads.retry}
            />
        </Box>
    )
}
