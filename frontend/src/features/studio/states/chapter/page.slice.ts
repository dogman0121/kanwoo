import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { studioClientAPI } from "../../api/client.api";
import { Entity } from "@/lib/types/Entity.type";
import { StudioChapter } from "../../types/studio-chapter.type";
import { openSnackbar } from "@/features/global/states/app/slice";
import { ApiError } from "@/lib/fetch/api-response.types";

export interface StudioChapterState {
    chapter?: Entity<StudioChapter>,
    ui: {
        isNotFound: boolean
    }
}

const initialState: StudioChapterState = {
    ui: {
        isNotFound: false
    }
}

type RootState = {
    studio: {chapter: {page: StudioChapterState}}
}

export const fetchChapter = createAsyncThunk(
    "studioChapter/fetchChapterStatus",
    async (chapterId: number) => {
        const response = await studioClientAPI.getChapter(chapterId)

        return {
            chapterId,
            response
        }
    }
)

export const updateChapter = createAsyncThunk(
    "studioChapter/updateChapterStatus",
    async (data: {chapterId: number, body: string, idempotencyKey: string}, thunkAPI) => {
        const {chapterId, body, idempotencyKey} = data

        try {
            const response = await studioClientAPI.updateChapter(chapterId, body, idempotencyKey)

            thunkAPI.dispatch(openSnackbar({type: "success", message: "Глава обновлена успешно"}))
            return {
                chapterId,
                response
            }
        } catch (e) {
            let errorMessage = "Неизвестная ошибка"
            if (e instanceof ApiError) {
                if (e.code == "already_exists")
                    errorMessage = "Глава уже существует"
            }
            thunkAPI.dispatch(openSnackbar({type: "error", message: `Ошибка: ${errorMessage}`}))
            throw e
        }
    }
)

export const studioProfileSlice = createSlice({
    name: "studio_profile",
    initialState,
    reducers: {
        setStudioChapter: (state, action) => {
            state.chapter = action.payload
        },
    },
    extraReducers: (builder) => (builder
        .addCase(fetchChapter.fulfilled, (state, action) => {
            const {response} = action.payload

            if (!response.data){
                state.chapter = undefined
                state.ui.isNotFound = true
                return
            }

            state.ui.isNotFound = false
            state.chapter = {
                data: response.data 
            }
        })
        .addCase(fetchChapter.rejected, (state, action) => {
            state.ui.isNotFound = true
        })
        .addCase(updateChapter.fulfilled, (state, action) => {
            const {response} = action.payload

            state.chapter = {
                data: response.data
            }
        })
    )
})

export const selectChapter = (state: RootState) => {
    return state.studio.chapter.page.chapter?.data
}

export const { 
    setStudioChapter
} = studioProfileSlice.actions

export default studioProfileSlice.reducer