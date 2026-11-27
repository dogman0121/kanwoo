import EditHeader from "@/components/edit/EditHeader";
import EditHeaderNav from "@/components/edit/EditHeaderNav";
import { Button } from "@mui/material";
import { useWatch } from "react-hook-form";
import UpdateChapterInfoForm, { type ChapterUpdateFormSchema, useUpdateChapterInfoForm } from "../forms/UpdateChapterInfoForm";
import { convertFormDataIntoJSON, prepareChapterUpdate } from "../forms/convertFormDataIntoJSON";
import { useChapterUploads } from "../forms/useChapterUploads";
import { useIdempotency } from "@/lib/use-idempotency.hook";
import { useAppDispatch, useAppSelector } from "@/lib/state/hooks";
import { selectChapter, updateChapter } from "../states/chapter/page.slice";
import EditPageContainer from "@/components/edit/EditPageContainer";

export default function ChapterInfoPage() {
    const dispatch = useAppDispatch()

    const chapter = useAppSelector(selectChapter)

    const methods = useUpdateChapterInfoForm(chapter)

    const {control, formState, reset} = methods

    const pages = useWatch({control: control, name: "pages"}) ?? []
    const uploads = useChapterUploads(pages)
    const idempotency = useIdempotency()

    if (!chapter) return

    const submit = async (data: ChapterUpdateFormSchema) => {
        const submission = prepareChapterUpdate(data, uploads.statuses)
        if (!submission) return

        const body = convertFormDataIntoJSON(submission)
        const result = await dispatch(updateChapter({
            chapterId: chapter.id,
            body,
            idempotencyKey: idempotency.getKey(body),
        }))
        if (updateChapter.fulfilled.match(result)) idempotency.reset()
    }

    return (
        <>
            <EditHeader>Основная информация</EditHeader>
            <EditHeaderNav
                buttons={
                    <>
                        <Button
                            variant="outlined"
                            disabled={!formState.isDirty || formState.isSubmitting}
                            type="reset"
                            onClick={() => reset()}
                        >
                            Отменить
                        </Button>
                        <Button
                            variant="contained"
                            loading={formState.isSubmitting}
                            disabled={!formState.isValid || !formState.isDirty || (pages.length > 0 && !uploads.ready)}
                            type="submit"
                            form="chapter-info"
                        >
                            Сохранить
                        </Button>
                    </>
                }
            />
            <EditPageContainer
                sx={{
                    py: 2
                }}
            >
                <UpdateChapterInfoForm 
                    methods={methods}
                    uploads={uploads}
                    onUpdate={submit}
                />
            </EditPageContainer>
        </>
    )
}
