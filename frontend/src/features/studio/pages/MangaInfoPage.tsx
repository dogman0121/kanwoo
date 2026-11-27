"use client"

import EditBody from "@/components/edit/EditBody"
import EditHeader from "@/components/edit/EditHeader"
import EditHeaderNav from "@/components/edit/EditHeaderNav"
import EditPageContainer from "@/components/edit/EditPageContainer"
import { Button } from "@mui/material"
import UpdateMangaInfoForm, { MangaUpdateInfoFormSchema, useUpdateMangaInfoForm } from "../forms/UpdateMangaInfoForm"
import { useAppDispatch, useAppSelector } from "@/lib/state/hooks"
import { selectManga, updateMangaInfo } from "../states/manga/page.slice"
import { useIdempotency } from "@/lib/use-idempotency.hook"
import prepareFileAction from "../lib/prepare-file-action"
import { routes, toHref } from "@/constants/routes/main.routes"

export default function MangaInfoPage() {
    const dispatch = useAppDispatch()

    const manga = useAppSelector(selectManga)

    const methods = useUpdateMangaInfoForm(manga)

    const {formState: {isDirty, isValid, isSubmitting}, reset} = methods

    const handleUpdateManga = async (data: MangaUpdateInfoFormSchema) => {
        if (!manga) return

        const response = await dispatch(
            updateMangaInfo({
                slug: manga.slug,
                form: data
            })
        ).unwrap()

        window.history.replaceState({}, "", toHref(routes.studio.manga.item, {slug: response.data.slug}))
    }

    return (
        <EditBody>
            <EditHeader>Основная информация</EditHeader>
            <EditHeaderNav
                buttons={
                    <>
                        <Button
                            variant="outlined"
                            disabled={!isDirty}
                            type="reset"
                            onClick={() => reset()}
                        >
                            Отменить
                        </Button>
                        <Button
                            variant="contained"
                            disabled={(!isValid || !isDirty)}
                            loading={isSubmitting}
                            type="submit"
                            form="manga-info"
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
                <UpdateMangaInfoForm 
                    methods={methods}
                    onUpdate={handleUpdateManga}
                />
            </EditPageContainer>
        </EditBody>
    )
}