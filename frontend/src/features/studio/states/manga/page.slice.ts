import { studioClientAPI } from "../../api/client.api";
import type { MangaUpdateInfoFormSchema } from "../../forms/UpdateMangaInfoForm";
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { StudioManga } from "../../types/studio-manga.type";
import { Entity } from "@/lib/types/Entity.type";
import prepareFileAction from "../../lib/prepare-file-action";

export interface StudioMangaState {
    manga?: Entity<StudioManga>,
    ui: {
        createTranslationDialogOpen: boolean
    }
}

const initialState: StudioMangaState = {
    ui: {
        createTranslationDialogOpen: false
    }
}

type RootState = {
    studio: {manga: {page: StudioMangaState}}
}

function convertUpdateInfoFormIntoFormdata(form: MangaUpdateInfoFormSchema) {

    const formData = new FormData()

    const body = JSON.stringify({
        name: form.name,
        slug: form.slug,
        description: form.description,
        privacy_id: Number(form.privacyId),
        year: Number(form.year),
        type_id: Number(form.typeId),
        status_id: Number(form.statusId),
        adult_id: Number(form.adultId),
        genres_ids: form.genresIds.map(Number),
        poster: { action: prepareFileAction(form.poster) },
        background: { action: prepareFileAction(form.background) },
        promo_logo: { action: prepareFileAction(form.promoLogo) },
        promo_background: { action: prepareFileAction(form.promoBackground) },
        promo_name: { action: prepareFileAction(form.promoName) },
    })

    formData.set("data", body)

    form.poster instanceof File && formData.set("poster", form.poster)
    form.background instanceof File && formData.set("background", form.background)
    form.promoName instanceof File && formData.set("promo_name", form.promoName)
    form.promoBackground instanceof File && formData.set("promo_background", form.promoBackground)
    form.promoLogo instanceof File && formData.set("promo_logo", form.promoLogo)

    return formData
}

export const updateMangaInfo = createAsyncThunk(
    "studio_manga/updateMangaInfo",
    async ({slug, form}: {slug: string, form: MangaUpdateInfoFormSchema}) => {
        return studioClientAPI.updateManga(slug, convertUpdateInfoFormIntoFormdata(form))
    }
)

export const studioMangaSlice = createSlice({
    name: "studio_manga",
    initialState,
    reducers: {
        setStudioManga: (state, action) => {
            state.manga = action.payload
        },
        setCreateTranslationDialogOpen: (state, action) => {
            state.ui.createTranslationDialogOpen = action.payload
        }
    },
    extraReducers: (builder) => builder.addCase(updateMangaInfo.fulfilled, (state, action) => {
        state.manga = { data: action.payload.data }
    })
})

export const selectManga = (state: RootState) => {
    return state.studio.manga.page.manga?.data
}

export const selectCreateTranslationDialogOpen = (state: RootState) => {
    return state.studio.manga.page.ui.createTranslationDialogOpen
}

export const { 
    setStudioManga,
    setCreateTranslationDialogOpen
} = studioMangaSlice.actions

export default studioMangaSlice.reducer