import { ApiConfig } from "@/lib/api/api-config.type";

export const globalApiConfig: ApiConfig = {
    "/uploads": {
        POST: {
            mode: "proxy",
            url: "/uploads"
        }
    },
    "/meta": {
        GET: {
            mode: "proxy",
            url: "/meta"
        }
    },
    "/feedbacks": {
        POST: {
            mode: "proxy",
            url: "/feedbacks"
        }
    }
}
