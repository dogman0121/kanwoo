import { Button, Dialog, DialogActions, DialogContent, DialogTitle } from "@mui/material"
import CreateMangaForm, { MangaCreateFormSchema, useCreateMangaForm } from "../forms/CreateMangaForm"

export default function CreateMangaDialog({
    open,
    onCreate,
    onClose
}: {
    open: boolean,
    onCreate?: (data: MangaCreateFormSchema) => void,
    onClose?: () => void
}) {
    const methods = useCreateMangaForm()

    const {formState} = methods

    return (
        <>
            <Dialog
                open={open}
                onClose={onClose}
                sx={{
                    "& .MuiDialog-paper": {
                        width: "960px",
                        maxWidth: "none"
                    },
                }}
            >
                <DialogTitle>Создание тайтла</DialogTitle>
                <DialogContent>
                    <CreateMangaForm 
                        onCreate={onCreate}
                        methods={methods}
                    />
                </DialogContent>
                <DialogActions>
                    <Button
                        variant="outlined"
                        onClick={onClose}
                    >
                        Отмена
                    </Button>
                    <Button
                        variant="contained"
                        type="submit"
                        form="manga-info"
                        loading={formState.isLoading}
                        disabled={!formState.isValid}
                    >
                        Создать
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    )
}