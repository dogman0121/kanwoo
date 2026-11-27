import { render, screen } from "@testing-library/react"
import { createElement } from "react"
import ChapterPagesInput from "@/features/studio/forms/inputs/ChapterPagesInput"

jest.mock("uuid", () => ({v4: jest.fn()}))

test("shows a poster placeholder for a studio page without a preview link", () => {
    render(createElement(ChapterPagesInput, {
        value: [{uuid: "missing", previewLink: "", name: "page.png"}],
        onChange: jest.fn(),
        uploads: {statuses: {}, retry: jest.fn(), ready: true},
    }))

    expect(screen.queryByTestId("NoPhotographyRoundedIcon")).not.toBeNull()
    expect(screen.queryByTestId("ZoomInRoundedIcon")).toBeNull()
})
