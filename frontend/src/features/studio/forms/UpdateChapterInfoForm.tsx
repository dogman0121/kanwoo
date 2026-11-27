import { Controller, useForm, UseFormReturn, useWatch } from "react-hook-form"
import PrivacySelect, { Privacy } from "@/components/PrivacySelect"
import type { useChapterUploads } from "./useChapterUploads"
import { useEffect } from "react"
import { Chapter } from "@/features/chapter/types/chapter.type"
import { Box, Checkbox } from "@mui/material"
import EditInput from "@/components/edit/Input"
import EditLabel from "@/components/edit/Label"
import EditCaption from "@/components/edit/Caption"
import ChapterPagesInput from "./inputs/ChapterPagesInput"
import { EditFile } from "@/components/edit/MultipleFilesInput"

export function convertDataIntoForm(chapter?: Chapter | null) {
    return {
        name: chapter?.name || "",
        chapter: chapter?.chapter ?? 1,
        isExtra: chapter?.extra_number != null,
        extraNumber: chapter?.extra_number ?? 1,
        privacyId: chapter?.privacy.id || Privacy.PRIVATE,
        pages: chapter?.pages?.map(p => ({
            previewLink: p.link, 
            name: p.orig_filename, 
            uuid: p.uuid
        })) || [],
    }
}

export type ChapterUpdateFormSchema = {
    name: string,
    chapter: number,
    isExtra: boolean,
    extraNumber: number,
    pages: EditFile[],
    privacyId: Privacy,
}

export function useUpdateChapterInfoForm(chapter?: Chapter | null) {
    const {reset, ...props} = useForm<ChapterUpdateFormSchema>({
        mode: "onChange",
        defaultValues: convertDataIntoForm(chapter)
    });

    useEffect(() => {
        if (chapter)
            reset(convertDataIntoForm(chapter))
    }, [chapter, reset])

    return {
        reset,
        ...props
    }
}

export default function UpdateChapterInfoForm({
    onUpdate,
    methods,
    uploads,
}: {
    methods: UseFormReturn<ChapterUpdateFormSchema>,
    onUpdate: (data: ChapterUpdateFormSchema) => Promise<void>
    uploads: ReturnType<typeof useChapterUploads>
}) {

    const {control, handleSubmit, formState, trigger} = methods

    const isExtra = useWatch({control, name: "isExtra"})

    return (
        <form id="chapter-info" onSubmit={handleSubmit(onUpdate)} inert={formState.isSubmitting}>
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    rowGap: 3
                }}
            >
                <Controller
                    control={control}
                    name="name"
                    render={({field: {value, ...props}, fieldState: {invalid, error}}) => (
                        <EditInput
                            label="Название главы"
                            caption="Если название не указано, в списке глав будет отображаться 'Нет названия'. "
                            inputProps={{
                                placeholder: "Введите название",
                                value: value,
                                error: invalid,
                                helperText: error?.message,
                                ...props
                            }}
                        />
                    )}
                />
                <Controller
                    control={control}
                    name="chapter"
                    rules={{required: true, validate: value => Number.isSafeInteger(Number(value))}}
                    render={({field, fieldState}) => (
                        <EditInput
                            label="Номер главы"
                            caption="Используется при сортировке глав. Порядковый номер главы."
                            inputProps={{
                                placeholder: "Введите номер",
                                type: "number",
                                error: fieldState.invalid,
                                ...field
                            }}
                        />
                    )}
                />
                <Controller
                    control={control}
                    name="privacyId"
                    rules={{required: true}}
                    render={({field}) => (
                        <PrivacySelect
                            sx={{
                                maxWidth: "400px"
                            }}
                            {...field}
                        />
                    )}
                />
                <Box>
                    <EditLabel>Дополнительная глава</EditLabel>
                    <EditCaption>
                        Данный раздел позволяет создать главу с уже существующим номером.
                        Будет считаться за доп главу с соответвующим модификатором
                    </EditCaption>
                    <Box
                        sx={{
                            mt: 2,
                            display: "flex",
                            flexDirection: "row",
                            gap: 2
                        }}
                    >
                        <Controller
                            control={control}
                            name="isExtra"
                            render={({field}) => (
                                <Checkbox
                                    checked={field.value}
                                    onBlur={field.onBlur}
                                    onChange={(_, checked) => {
                                        field.onChange(checked)
                                        trigger("extraNumber")
                                    }}
                                />
                            )}
                        />
                        <Controller
                            control={control}
                            name="extraNumber"
                            rules={{validate: (value, form) => !form.isExtra ||
                                (String(value).trim() !== "" && Number.isSafeInteger(Number(value)))}}
                            render={({field, fieldState}) => (
                                <EditInput
                                    inputProps={{
                                        placeholder: "Экстра номер",
                                        disabled: !isExtra,
                                        type: "number",
                                        error: fieldState.invalid,
                                        ...field
                                    }}
                                />
                            )}
                        />
                    </Box>
                </Box>
                <Controller
                    control={control}
                    name="pages"
                    render={({field: {value, onChange}}) => (
                        <ChapterPagesInput value={value ?? []} onChange={onChange} uploads={uploads} />
                    )}
                />
            </Box>
        </form>
    )
}
