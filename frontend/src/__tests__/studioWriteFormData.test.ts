import { createMangaFormData, updateMangaFormData, updateProfileFormData } from "@/features/studio/lib/write-form-data"

const poster = new File(["poster"], "poster.jpg", {type: "image/jpeg"})
const manga = {
    name: "Manga",
    description: "",
    year: 2025,
    privacy: 1,
    type: 1,
    status: 1,
    adult: 1,
    genres: [2, 7],
    poster,
}

test("creates a manga with all selected genres and separate file parts", () => {
    const background = new File(["background"], "background.jpg", {type: "image/jpeg"})
    const body = createMangaFormData({...manga, background})

    expect(JSON.parse(body.get("data") as string)).toMatchObject({genres_ids: [2, 7]})
    expect(Array.from(body.keys())).toEqual(["data", "poster", "background"])
    expect(body.get("poster")).toBe(poster)
    expect(body.get("background")).toBe(background)
})

test("updates a manga without uploading existing URLs or deleted images", () => {
    const body = updateMangaFormData({
        ...manga,
        slug: "manga",
        background: "/background.jpg",
        promoName: null,
        promoLogo: "/logo.webp",
        promoBackground: null,
        nameTranslations: [{lang: 1, name: "Translation"}],
    })

    expect(JSON.parse(body.get("data") as string)).toMatchObject({
        genres_ids: [2, 7],
        name_translations: [{lang: 1, name: "Translation"}],
        poster_action: "update",
        background_action: "keep",
        promo_name_action: "delete",
    })
    expect(Array.from(body.keys())).toEqual(["data", "poster"])
})

test("uses the profile avatar removal action and preserves links as an array", () => {
    const links = [{name: "Website", link: "https://example.com"}]
    const body = updateProfileFormData({name: "Profile", slug: "profile", about: "", avatar: null, links})

    expect(JSON.parse(body.get("data") as string)).toMatchObject({avatar_action: "remove", links})
    expect(Array.from(body.keys())).toEqual(["data"])
})
