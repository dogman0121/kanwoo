import { Controller, useForm, UseFormReturn } from "react-hook-form"
import MangaPoster from "../components/ui/manga/Poster"
import MangaName from "../../manga/forms/components/MangaName"
import MangaDescription from "../../manga/forms/components/MangaDescription"
import { Box, Grid } from "@mui/material"
import MangaType from "../../manga/forms/components/MangaType"
import MangaStatus from "../../manga/forms/components/MangaStatus"
import MangaYear from "../../manga/forms/components/MangaYear"
import MangaAdult from "../../manga/forms/components/MangaAdult"
import MangaGenres from "../../manga/forms/components/MangaGenres"
import MangaBackground from "../components/ui/manga/Background"
import PrivacySelect, { Privacy } from "@/components/PrivacySelect"


export function getDefaultValues() {
    return {
        name: "",
        description: "",
        type: 1,
        status: 1,
        adult: 1,
        genres: [],
        year: new Date().getFullYear()
    }
}

export interface MangaCreateFormSchema {
    name: string,
    privacyId: number,
    description: string,
    year: number,
    typeId: number,
    statusId: number,
    adultId: number,
    genresIds: number[],
    poster: File,
    background: File
}

export function useCreateMangaForm() {
    const props = useForm<MangaCreateFormSchema>({
        mode: "onChange",
        defaultValues: getDefaultValues()
    });

    return props
}

export default function CreateMangaForm({
    onCreate,
    methods
}: {
    onCreate?: (data: MangaCreateFormSchema) => void,
    methods: UseFormReturn<MangaCreateFormSchema>
}) {

    const {handleSubmit, control} = methods

    const onSubmit = async (data: MangaCreateFormSchema) => {
        onCreate?.(data)
    }

    return (
        <>
            <form id="manga-info" onSubmit={handleSubmit(onSubmit)}>
                <Box
                    sx={{
                        display: "flex",
                        flexDirection: "column",
                        rowGap: 3
                    }}
                >
                    <Controller
                        name="poster"
                        control={control}
                        render={({field: {value, onChange}}) => (
                            <MangaPoster 
                                value={value}
                                onChange={onChange}
                            />
                        )}
                    />
                    <Controller 
                        control={control}
                        name="name"
                        rules={{
                            required: "Это поле не должно быть пустым"
                        }}
                        render={({field: {value, ...props}, fieldState: {invalid, error}}) => (
                            <MangaName
                                value={value}
                                {...props}
                                error={invalid}
                                helperText={error?.message}
                            />
                        )}
                    />
                    <Controller 
                        control={control}
                        name="privacyId"
                        defaultValue={Privacy.PRIVATE}
                        render={({field}) => (
                            <PrivacySelect 
                                sx={{
                                    maxWidth: "400px"
                                }}
                                {...field}
                            />
                        )}
                    />
                    <Controller 
                        control={control}
                        name="description"
                        rules={{
                            maxLength: 1000
                        }}
                        render={({field: {value, ...props}, fieldState: {invalid, error}}) => (
                            <MangaDescription 
                                value={value}
                                {...props}
                                error={invalid}
                                helperText={error?.type == "maxLength" && "Описание не может быть больше 1000 символов"}
                            />
                        )}
                    />
                    <Grid 
                        container 
                        columnSpacing={3} 
                        rowSpacing={2}
                        columns={{md: 3, xs: 1}}
                    >
                        <Grid size={1}>
                            <Controller 
                                name="typeId"
                                control={control}
                                render={({field: {value, ...props}}) => (
                                    <MangaType
                                        label="Тип"
                                        value={value}
                                        {...props}
                                    />
                                )}
                            />
                        </Grid>
                        <Grid size={1}>
                            <Controller 
                                name="statusId"
                                control={control}
                                render={({field: {value, ...props}}) => (
                                    <MangaStatus
                                        label="Статус"
                                        value={value}
                                        {...props}
                                    />
                                )}
                            />
                        </Grid>
                        <Grid size={1}>
                            <Controller 
                                name="year"
                                control={control}
                                render={({field: {value, ...props}}) => (
                                    <MangaYear 
                                        value={value}
                                        {...props}
                                    />
                                )}
                            />
                        </Grid>
                        <Grid size={1}>
                            <Controller 
                                name="adultId"
                                control={control}
                                render={({field: {value, ...props}}) => (
                                    <MangaAdult
                                        value={value}
                                        {...props}
                                    />
                                )}
                            />
                        </Grid>
                    </Grid>
                    <Controller 
                        name="genresIds"
                        control={control}
                        render={({field: {value, onChange, ...props}}) => (
                            <MangaGenres
                                value={value}
                                onChange={onChange}
                                {...props}
                            />
                        )}
                    />
                    <Controller 
                        name="background"
                        control={control}
                        render={({field: {value, onChange}}) => (
                            <MangaBackground
                                value={value}
                                onChange={onChange}
                            />
                        )}
                    />
                </Box>
            </form>
        </>
    )
}