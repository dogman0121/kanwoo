import { Button, Dialog, DialogActions, DialogContent, DialogTitle } from "@mui/material"
import { useWatch } from "react-hook-form"
import CreateChapterForm, { ChapterCreateFormSchema, useCreateForm } from "../forms/CreateChapterForm"
import type { ChapterCreateSubmission } from "../forms/convertFormDataIntoJSON"
import { useChapterUploads } from "../forms/useChapterUploads"

export default function CreateChapterDialog({
    open,
    onSubmit,
    onClose,
    translationID,
}: {
    open: boolean,
    translationID: number,
    onSubmit: (data: ChapterCreateSubmission) => Promise<void>,
    onClose: () => void,
}) {
    const methods = useCreateForm({translationID})
    const {isSubmitting, isValid, isLoading} = methods.formState

    const pages = useWatch({control: methods.control, name: "pages"})

    const uploads = useChapterUploads(pages)

    const submit = async (data: ChapterCreateFormSchema) => {
        if (!uploads.ready) return

        const pages = data.pages.flatMap(page => {
            const dimensions = uploads.statuses[page.uuid]?.dimensions
            return dimensions ? [{uuid: page.uuid, ...dimensions}] : []
        })

        if (pages.length !== data.pages.length) return

        try {
            await onSubmit({...data, pages})
        } catch {
            // The request reports its error through the app snackbar.
        }
    }

    return (
        <Dialog
            open={open}
            onClose={isSubmitting ? undefined : onClose}
            fullWidth
            maxWidth="md"
            sx={{
                "& .MuiDialog-paper": {
                    width: "100%"
                }
            }}
        >
            <DialogTitle>Создание главы</DialogTitle>
            <DialogContent>
                {!isLoading && (
                    <CreateChapterForm 
                        onSubmit={submit}
                        methods={methods} 
                        uploads={uploads} 
                    />
                )}
            </DialogContent>
            <DialogActions>
                <Button variant="outlined" onClick={onClose} disabled={isSubmitting}>Отмена</Button>
                <Button
                    variant="contained"
                    type="submit"
                    form="chapter-info"
                    loading={isSubmitting}
                    disabled={isLoading || !isValid || !uploads.ready}
                >
                    Отправить
                </Button>
            </DialogActions>
        </Dialog>
    )
}
