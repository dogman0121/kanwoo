import { render, screen } from "@testing-library/react"
import { createElement } from "react"
import ReaderPage from "@/features/reader/components/ReaderPage"
import PageLoader from "@/features/reader/lib/page-loader"

const page = {uuid: "missing", link: "", width: 800, height: 1200, orig_filename: "page.png"}

test("leaves an unlinked reader page blank", () => {
    render(createElement(ReaderPage, {page}))

    expect(screen.queryByTestId("NoPhotographyRoundedIcon")).toBeNull()
    expect(screen.queryByRole("img", {name: "Страница"})).toBeNull()
})

test("skips unlinked pages without removing neighboring pages from the load queue", () => {
    const loop = jest.spyOn(PageLoader.prototype, "_loadingLoop").mockResolvedValue(undefined)
    try {
        const loader = new PageLoader({preloadAfterSize: 1, preloadBeforeSize: 0, maxRetries: 1})
        const linked = {...page, uuid: "linked", link: "/page.png"}
        loader.addChapter(1, [page, linked])
        loader.setPage(1, 0)

        expect(loader.tasks.size()).toBe(1)
        expect(loader.tasks.front()?.page).toBe(linked)
    } finally {
        loop.mockRestore()
    }
})
