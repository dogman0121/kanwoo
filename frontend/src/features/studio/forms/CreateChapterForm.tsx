import { Controller, useForm, UseFormReturn, useWatch } from "react-hook-form"
import PrivacySelect, { Privacy } from "@/components/PrivacySelect"
import type { EditFile } from "@/components/edit/MultipleFilesInput"
import { useAppDispatch } from "@/lib/state/hooks"
import { fetchChapterCreateForm } from "../states/translation/chapters.slice"
import type { useChapterUploads } from "./useChapterUploads"
import { Box, Checkbox } from "@mui/material"
import EditInput from "@/components/edit/Input"
import EditLabel from "@/components/edit/Label"
import EditCaption from "@/components/edit/Caption"
import ChapterPagesInput from "./inputs/ChapterPagesInput"
import { ChapterCreateSubmission } from "./convertFormDataIntoJSON"


export function getDefaultValues() {
    return {
        name: "",
        chapter: 1,
        isExtra: false,
        extraNumber: 1,
        pages: [],
        privacyId: Privacy.PRIVATE,
    }
}

export type ChapterCreateFormSchema = {
    name: string,
    chapter: number,
    isExtra: boolean,
    extraNumber: number,
    pages: EditFile[],
    privacyId: Privacy,
}

export function convertFormDataIntoJSON(data: ChapterCreateFormSchema) {
    return JSON.stringify({
        name: data.name.trim() || null,
        chapter: Number(data.chapter),
        privacy_id: Number(data.privacyId),
        extra_number: data.isExtra ? Number(data.extraNumber) : null,
        pages: data.pages,
    })
}

export function useCreateForm({
    translationID
}: {
    translationID: number
}) {
    const dispatch = useAppDispatch()
    const props = useForm<ChapterCreateFormSchema>({
        mode: "onChange",
        defaultValues: async () => {
            const data = await dispatch(fetchChapterCreateForm(translationID)).unwrap()

            return {
                name: data.name,
                chapter: data.chapter,
                isExtra: data.extra_number != null,
                extraNumber: data.extra_number ?? 0,
                pages: data.pages.map(p => ({
                    uuid: p.uuid,
                    previewLink: p.link,
                    name: p.orig_filename
                } as EditFile)),
                privacyId: data.privacy_id
            }
        }
    });

    return props
}

export default function CreateChapterForm({
    onSubmit,
    methods,
    uploads,
}: {
    onSubmit: (data: ChapterCreateFormSchema) => Promise<void>
    methods: UseFormReturn<ChapterCreateFormSchema>
    uploads: ReturnType<typeof useChapterUploads>
}) {
    const {control} = methods

    const onSubmitWrapper = async (data: ChapterCreateFormSchema) => {
        await onSubmit?.(data)

        const {defaultValues} = methods.formState
        const currentChapterNumber = Number(data.chapter ?? 0);

        methods.reset({
            ...defaultValues,
            name: "",      
            pages: [],
            isExtra: false,
            extraNumber: 0,
            chapter: currentChapterNumber + 1
        })
    }

    const isExtra = useWatch({control, name: "isExtra"})

    return (
        <form id="chapter-info" onSubmit={methods.handleSubmit(onSubmitWrapper)} inert={methods.formState.isSubmitting}>
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    rowGap: 3
                }}
            >
                <Controller
                    control={methods.control}
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
                    control={methods.control}
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
                    control={methods.control}
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
                            control={methods.control}
                            name="isExtra"
                            render={({field}) => (
                                <Checkbox
                                    checked={field.value}
                                    onBlur={field.onBlur}
                                    onChange={(_, checked) => {
                                        field.onChange(checked)
                                        methods.trigger("extraNumber")
                                    }}
                                />
                            )}
                        />
                        <Controller
                            control={methods.control}
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
                    control={methods.control}
                    name="pages"
                    render={({field: {value, onChange}}) => (
                        <ChapterPagesInput value={value ?? []} onChange={onChange} uploads={uploads} />
                    )}
                />
            </Box>
        </form>
    )
}
