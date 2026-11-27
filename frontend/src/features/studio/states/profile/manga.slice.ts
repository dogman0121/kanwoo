import { createAsyncThunk, createEntityAdapter, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { StudioManga } from "../../types/studio-manga.type";
import { Entity } from "@/lib/types/Entity.type";
import { studioClientAPI } from "../../api/client.api";
import { MangaCreateFormSchema } from "../../forms/CreateMangaForm";
import { openSnackbar } from "@/features/global/states/app/slice";
import { ApiError } from "@/lib/fetch/api-response.types";

const mangaAdapter = createEntityAdapter({
    selectId: (manga: Entity<StudioManga>) => manga.data.id
})

const initialState = mangaAdapter.getInitialState()

type RootState = {
    studio: {profile: {manga: typeof initialState}}
}

function convertCreateFormIntoFormData(form: MangaCreateFormSchema) {
    const formData = new FormData()

    const body = JSON.stringify({
        name: form.name,
        privacy_id: form.privacyId,
        description: form.description,
        year: form.year,
        type_id: form.typeId,
        status_id: form.statusId,
        adult_id: form.adultId,
        genres_ids: form.genresIds,
    })

    formData.set("data", body)

    form.poster && formData.set("poster", form.poster)
    form.background && formData.set("background", form.background)

    return formData
}


export const createManga = createAsyncThunk(
    "studioProfileManga/createMangaStatus",
    async (data: {idempotencyKey: string, profileSlug: string, form: MangaCreateFormSchema}, thunkAPI) => {
        const {profileSlug, form, idempotencyKey} = data
        
        const formData = convertCreateFormIntoFormData(form)

        try {
            const response = await studioClientAPI.createManga(profileSlug, formData, idempotencyKey)

            thunkAPI.dispatch(openSnackbar({type: 'success', message: "Глава добавлена успешно"}))

            return {
                response: response
            }
        } catch (e) {
            let errorMessage = "Неизвестная ошибка"
            if (e instanceof ApiError) {
                if (e.code == "already_exists") 
                    errorMessage = "Манга уже существует"
            }
            thunkAPI.dispatch(openSnackbar({type: "error", message: `Произошла ошибка: ${errorMessage}`}))
            throw e
        }
    }
)

export const loadManga = createAsyncThunk(
    "studioProfileManga/loadMangaStatus",
    async (profileSlug: string, thunkAPI) => {
        const response = await studioClientAPI.getProfileManga(profileSlug)

        return {
            response
        }
    }
)

export const profileMangaSlice = createSlice({
    name: "studioProfileManga",
    initialState,
    reducers: {
        setMangaList: (state, action: PayloadAction<Entity<StudioManga>[]>) => {
            mangaAdapter.setMany(state, action.payload)
        },
        addManga: (state, action: PayloadAction<Entity<StudioManga>>) => {
            mangaAdapter.addOne(state, action.payload)
        }
    },
    extraReducers: (builder) => (builder
        .addCase(loadManga.fulfilled, (state, action) => {
            const {response} = action.payload

            const preparedManga = []
            for (let i = 0; i < response.data.length; i++) {
                preparedManga.push({
                    data: response.data[i],
                })
            }

            mangaAdapter.setMany(
                state,
                preparedManga
            )
        })
        .addCase(createManga.fulfilled, (state, action) => {
            const {response} = action.payload
            
            mangaAdapter.addOne(state, {
                data: response.data
            })
        })
    )
})

export const {
    selectAll: selectManga
} = mangaAdapter.getSelectors((state: RootState) => state.studio.profile.manga)

export const { 
    setMangaList,
    addManga
} = profileMangaSlice.actions

export default profileMangaSlice.reducer