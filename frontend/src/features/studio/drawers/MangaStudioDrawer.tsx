"use client"

import EditLayout from "@/components/edit/EditLayout"
import { notFound, useParams } from "next/navigation";
import { ApiError } from "@/lib/fetch/api-response.types";
import { Avatar, Box, Divider, List, ListItemIcon, ListItemText, Skeleton, Typography } from "@mui/material";
import ProfilePermission from "@/types/profile/profilePermission";
import { clientFetch } from "@/lib/fetch/client-fetch.util";
import { useEffect, useState } from "react";
import { Profile } from "@/types/profile";
import { useAppDispatch, useAppSelector } from "@/lib/state/hooks";
import { selectDrawerOpen, setDrawerOpen } from "@/features/studio/states/studio-page.slice";
import useSection from "@/features/studio/hooks/useSection";
import EditDrawer from "@/components/edit/EditDrawer";
import EditDrawerContainer from "@/components/edit/EditDrawerContainer";
import { routes, toHref } from "@/constants/routes/main.routes";
import InfoOutlineRoundedIcon from '@mui/icons-material/InfoOutlineRounded';
import LibraryBooksRoundedIcon from '@mui/icons-material/LibraryBooksRounded';
import TranslateRoundedIcon from '@mui/icons-material/TranslateRounded';
import CollectionsBookmarkRoundedIcon from '@mui/icons-material/CollectionsBookmarkRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import EditSectionsLinkButton from "@/components/edit/EditSectionsLinkButton";
import EditSectionsButton from "@/components/edit/EditSectionsButton";
import { studioClientAPI } from "@/features/studio/api/client.api";
import { selectProfile, setStudioProfile, setStudioProfilePermissions } from "@/features/studio/states/profile/page.slice";
import { selectManga, setStudioManga } from "@/features/studio/states/manga/page.slice";
import Poster from "@/features/manga/components/ui/Poster";
import { BottomOptionsContainer } from "./ui/BottomOptions";
import { Manga } from "@/features/manga/types";

export function StudioDrawerSkeleton() {
    const { section } = useSection()

    return (
        <EditDrawer>
            <EditDrawerContainer>
                <Box
                    sx={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center"
                    }}
                >
                    <Skeleton 
                        variant="rounded"
                        width={96}
                        height={144}
                    />
                    <Box
                        sx={{
                            mt: 2,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                        }}
                    >
                        <Typography><Skeleton variant="text" width={100}/></Typography>
                        <Typography variant="caption" color="textSecondary">
                            <Skeleton variant="text" width={75}/>
                        </Typography>
                    </Box>
                </Box>
                <List>
                    <EditSectionsButton 
                        selected={section == "main"}
                    >
                        <ListItemIcon>
                            <InfoOutlineRoundedIcon />
                        </ListItemIcon>
                        <ListItemText>
                            <Skeleton variant="text" width={75}/>
                        </ListItemText>
                    </EditSectionsButton>
                    <EditSectionsButton 
                        selected={section == "translations"}
                    >
                        <ListItemIcon>
                            <TranslateRoundedIcon />
                        </ListItemIcon>
                        <ListItemText>
                            <Skeleton variant="text" width={75}/>
                        </ListItemText>
                    </EditSectionsButton>
                </List>
            </EditDrawerContainer>
            <BottomOptionsContainer>
                <List>
                    <EditSectionsButton>
                        <ListItemIcon>
                            <SettingsRoundedIcon />
                        </ListItemIcon>
                        <ListItemText>
                            <Skeleton variant="text" width={75}/>
                        </ListItemText>
                    </EditSectionsButton>
                </List>
            </BottomOptionsContainer>
        </EditDrawer>
    )
}

export function StudioDrawer({manga}: {manga: Manga}) {

    const { section } = useSection()

    if (!manga) return

    return (
        <EditDrawer>
            <EditDrawerContainer>
                <Box
                    sx={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center"
                    }}
                >
                    <Poster 
                        src={manga.poster?.medium}
                        width="96px"
                    />
                    <Box
                        sx={{
                            mt: 2,
                            textAlign: "center"
                        }}
                    >
                        <Typography>{manga.name}</Typography>
                        <Typography variant="caption" color="textSecondary">
                            @{manga.slug}
                        </Typography>
                    </Box>
                </Box>
                <List>
                    <EditSectionsLinkButton 
                        link={toHref(routes.studio.manga.item, {slug: manga.slug})}
                        selected={section == "main"}
                    >
                        <ListItemIcon>
                            <InfoOutlineRoundedIcon />
                        </ListItemIcon>
                        <ListItemText>
                            Информация
                        </ListItemText>
                    </EditSectionsLinkButton>
                    <EditSectionsLinkButton 
                        link={toHref(routes.studio.manga.translations, {slug: manga.slug})}
                        selected={section == "translations"}
                    >
                        <ListItemIcon>
                            <TranslateRoundedIcon />
                        </ListItemIcon>
                        <ListItemText>
                            Переводы
                        </ListItemText>
                    </EditSectionsLinkButton>
                </List>
            </EditDrawerContainer>
            <BottomOptionsContainer>
                <List>
                    <EditSectionsButton>
                        <ListItemIcon>
                            <SettingsRoundedIcon />
                        </ListItemIcon>
                        <ListItemText>
                            Настройки
                        </ListItemText>
                    </EditSectionsButton>
                </List>
            </BottomOptionsContainer>
        </EditDrawer>
    )
}

export default function MangaStudioDrawer() {
    const manga = useAppSelector(selectManga)

    if (!manga)
        return <StudioDrawerSkeleton />

    return <StudioDrawer manga={manga}/>
}