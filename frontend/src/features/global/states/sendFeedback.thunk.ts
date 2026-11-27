import { clientFetch } from "@/lib/fetch/client-fetch.util"
import { createAsyncThunk } from "@reduxjs/toolkit"

export const sendFeedback = createAsyncThunk("feedback/send", async (message: string) => {
    const csrfCookie = process.env.NEXT_PUBLIC_CSRF_ACCESS_COOKIE_NAME
    const csrf = Boolean(csrfCookie && clientFetch._getCookie(csrfCookie))
    await clientFetch.post("/feedbacks", {
        body: JSON.stringify({message}),
    }, {use_json: true, csrf})
})
