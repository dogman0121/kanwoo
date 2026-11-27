import { convertFormDataIntoJSON, prepareChapterUpdate, type ChapterCreateSubmission } from "@/features/studio/forms/convertFormDataIntoJSON"

const form: ChapterCreateSubmission = {
    name: " ",
    chapter: 4,
    privacyId: 1,
    isExtra: false,
    extraNumber: 2,
    pages: [
        {uuid: "page-b", width: 800, height: 1000},
        {uuid: "page-a", width: 800, height: 1200},
    ],
}

test("keeps page order and serializes empty optional fields as null", () => {
    expect(JSON.parse(convertFormDataIntoJSON(form))).toEqual({
        name: null,
        chapter: 4,
        privacy_id: 1,
        extra_number: null,
        pages: form.pages,
    })
})

test("trims the chapter name and includes the extra chapter number", () => {
    const json = convertFormDataIntoJSON({...form, name: " Дополнение ", isExtra: true})

    expect(JSON.parse(json)).toMatchObject({name: "Дополнение", extra_number: 2})
})

test("keeps existing UUIDs and serializes uploaded pages in edit order", () => {
    const existing = {uuid: "existing", name: "page.png", previewLink: "/page.png"}
    const uploaded = {
        uuid: "new",
        name: "page.png",
        previewLink: "blob:new",
        file: new File(["image"], "page.png"),
    }
    const updatedForm = {...form, isExtra: true, extraNumber: 0, pages: [uploaded, existing]}
    const submission = prepareChapterUpdate(updatedForm, {
        new: {state: "ready", dimensions: {width: 800, height: 1200}},
    })
    expect(submission && JSON.parse(convertFormDataIntoJSON(submission))).toMatchObject({
        extra_number: 0,
        pages: [
            {uuid: "new", is_new: true, width: 800, height: 1200},
            {uuid: "existing", is_new: false},
        ],
    })

    expect(prepareChapterUpdate(updatedForm, {})).toBeUndefined()
    expect(prepareChapterUpdate(updatedForm, {new: {state: "error"}})).toBeUndefined()
})
