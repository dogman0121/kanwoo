"use client"

import EditLayout from "@/components/edit/EditLayout"
import { notFound, useParams } from "next/navigation";
import { ApiError } from "@/lib/fetch/api-response.types";
import { Avatar, Box, Divider, List, ListItemIcon, ListItemText, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "@/lib/state/hooks";
import { studioClientAPI } from "@/features/studio/api/client.api";
import { selectManga, setStudioManga } from "@/features/studio/states/manga/page.slice";
import StudioDrawer from "@/features/studio/drawers/MangaStudioDrawer";



export default function Layout({
    children
}: {
    children: React.ReactNode
}) {
    const dispatch = useAppDispatch()

    const { slug } = useParams<{slug: string}>()

    const [isNotFound, setIsNotFound] = useState(false)

    const fetchProfile = async (slug: string) => {
        try {
            const response = await studioClientAPI.getManga(slug)

            if (!response.data)
                return setIsNotFound(true)

            dispatch(setStudioManga({
                data: response.data,
                context: response.context,
                permission: response.permission
            }))
            setIsNotFound(false)
        } catch (e) {
            if (e instanceof ApiError) {
                return setIsNotFound(true)
            }

            throw e
        }
        
    }

    useEffect(() => {
        fetchProfile(slug)
    }, [slug])

    if (isNotFound) {
        notFound()
    }

    return (
        <EditLayout>
            <StudioDrawer/>
            <Box
                sx={{
                    width: "100%"
                }}
            >
                {children}
            </Box>
        </EditLayout>
    )
}