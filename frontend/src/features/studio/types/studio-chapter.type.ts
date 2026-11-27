import { Chapter } from "@/features/chapter/types/chapter.type";

export type StudioChapterListItem = Pick<StudioChapter, "id" | "name" | "chapter" | "extra_number" | "privacy">

export type StudioChapter = Chapter & {
    stats: {
        views: number,
        comments: number
    }
}
