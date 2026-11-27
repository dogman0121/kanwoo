import EditHeader from "@/components/edit/EditHeader";
import EditHeaderNav from "@/components/edit/EditHeaderNav";
import EditPageContainer from "@/components/edit/EditPageContainer";
import Poster from "@/features/manga/components/ui/Poster";
import { Privacy } from "@/components/PrivacySelect";
import WrappedText from "@/components/WrapperTypography";
import { routes, toHref } from "@/constants/routes/main.routes";
import CreateMangaDialog from "@/features/studio/components/CreateMangaDialog";
import { Manga } from "@/features/manga/types";
import StudioList from "@/features/studio/components/List";
import StudioPrivacyStatus from "@/features/studio/components/ui/PrivacyStatus";
import { addManga, createManga, loadManga, selectManga } from "@/features/studio/states/profile/manga.slice";
import { selectCreateMangaDialogOpen, selectProfile, setCreateMangaDialogOpen } from "@/features/studio/states/profile/page.slice";
import { StudioManga } from "@/features/studio/types/studio-manga.type";
import { useAppDispatch, useAppSelector } from "@/lib/state/hooks";
import { Box, Button, Divider, Grid, Stack, SxProps, Typography } from "@mui/material";
import Link from "next/link";
import React, { Children, useEffect, useState, useTransition } from "react";
import { MangaCreateFormSchema } from "@/features/studio/forms/CreateMangaForm";
import { studioClientAPI } from "@/features/studio/api/client.api";
import { openSnackbar } from "@/features/global/states/app/slice";
import { useSearchParams } from "next/navigation";
import ProfileSlug from "../components/ui/profile/ProfileSlug";
import { useIdempotency } from "@/lib/use-idempotency.hook";
import EditBody from "@/components/edit/EditBody";


function MangaGrid({children}: {children: React.ReactNode}) {
    return (
        <Box
            sx={{
                px: 5,
                py: 1
            }}
        >
            <Grid
                container
                columns={14}
                spacing={3}
                sx={{
                    alignItems: "center"
                }}
            >
                {Children.map(children, c => c)}
            </Grid>
        </Box>
    )
}

function MangaGridRow({manga}: {manga: StudioManga}){ 

    return (
        <MangaGrid>
            <Grid
                size={6}
            >
                <Box
                    sx={{
                        display: "flex",
                        flexDirection: "row",
                        alignItems :"center",
                        gap: 2
                    }}
                >
                    <Poster 
                        width="80px"
                        src={manga.poster?.medium}
                    />
                    <Box
                        sx={{
                            display: "flex",
                            flexDirection: "column",
                            rowGap: "5px"
                        }}
                    >
                        <Typography variant="caption">
                            {manga.type?.name} / {manga.year}
                            </Typography>
                        <Link href={toHref(routes.studio.manga.item, {slug: manga.slug})}>
                            <Typography
                                variant="h3"
                                sx={{
                                    "&:hover": {
                                        textDecoration: "underline"
                                    }
                                }}
                            >
                                {manga.name}
                            </Typography>
                        </Link>
                        <WrappedText
                            lines={2}
                            variant="caption"
                            color="textSecondary"
                        >
                            {manga.description}
                        </WrappedText>
                    </Box>
                </Box>
            </Grid>
            <Grid size={2}>
                <StudioPrivacyStatus privacy={manga.privacy.id as Privacy}/>
            </Grid>
            <Grid size={2}>
                <Typography>{manga.moderation_status.status_type.name}</Typography>
            </Grid>
            <Grid size={2}>
                <Typography>{manga.stats?.comments}</Typography>
            </Grid>
            <Grid size={2}>
                <Typography>{manga.stats?.views}</Typography>    
            </Grid>                
        </MangaGrid>
    )
}

export default function ProfileMangaPage() {
    const dispatch = useAppDispatch()

    const searchParams = useSearchParams()

    const {getKey} = useIdempotency()

    const profile = useAppSelector(selectProfile)
    const createMangaDialogOpen = useAppSelector(selectCreateMangaDialogOpen)

    useEffect(() => {
        if (!profile)
            return

        dispatch(
            loadManga(
                profile.slug
            )
        )
    }, [profile])

    const manga = useAppSelector(selectManga)

    const handleCreateManga = async (data: MangaCreateFormSchema) => {
        if (!profile) return

        const body = JSON.stringify({
            name: data.name,
            privacy_id: data.privacyId,
            description: data.description,
            year: data.year,
            type_id: data.typeId,
            status_id: data.statusId,
            adult_id: data.adultId,
            genres_ids: data.genresIds,
            poster_hash: data.poster && await crypto.subtle.digest(
                'SHA-256', await data.poster.arrayBuffer()
            ),
            background_hash: data.background && await crypto.subtle.digest(
                'SHA-256', await data.background.arrayBuffer()
            ),
        })

        await dispatch(
            createManga({
                idempotencyKey: getKey(body),
                profileSlug: profile.slug, 
                form: data
            })
        ).unwrap()
    }

    useEffect(() => {
        const url = new URL(window.location.href);

        if (createMangaDialogOpen) {
            url.searchParams.set("createManga", "true")
        } else {
            url.searchParams.delete("createManga")
        }

        window.history.replaceState({}, '', url);
    }, [createMangaDialogOpen])

    useEffect(() => {
        dispatch(setCreateMangaDialogOpen(searchParams.get("createManga") == "true"))
    }, [searchParams])

    return (
        <EditBody>
            <EditHeader>Мои тайтлы</EditHeader>
            <EditHeaderNav 
                buttons={
                    <>
                        <Button
                            variant="contained"
                            onClick={() => dispatch(setCreateMangaDialogOpen(true))}
                        >
                            Создать
                        </Button>
                    </>
                }
            />
            <MangaGrid>
                <Grid size={6}>
                    <Typography variant="caption">Тайтл</Typography>
                </Grid>
                <Grid size={2}>
                    <Typography variant="caption">Доступ</Typography>
                </Grid>
                <Grid size={2}>
                    <Typography variant="caption">Модерация</Typography>
                </Grid>
                <Grid size={2}>
                    <Typography variant="caption">Комментарии</Typography>
                </Grid>
                <Grid size={2}>
                    <Typography variant="caption">Просмотры</Typography>
                </Grid>
            </MangaGrid>
            <Divider />
            <StudioList
            >
                {manga?.map((m) => (
                    <MangaGridRow key={m.data.slug} manga={m.data}/>
                ))}
            </StudioList>
            <CreateMangaDialog 
                open={createMangaDialogOpen}
                onCreate={handleCreateManga}
                onClose={() => dispatch(setCreateMangaDialogOpen(false))}
            />
        </EditBody>
    )
}