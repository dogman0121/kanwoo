"use client"

import { closestCenter, DndContext, DragEndEvent, KeyboardSensor, PointerSensor, useSensor, useSensors } from "@dnd-kit/core"
import {CSS} from '@dnd-kit/utilities';
import { Box, Button, Chip, CircularProgress, Modal, Paper, Slider, Stack, SxProps, Typography } from "@mui/material";
import UploadFileRoundedIcon from "@mui/icons-material/UploadFileRounded"
import { useDropzone } from "react-dropzone";
import { v4 } from "uuid";
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable } from "@dnd-kit/sortable";
import { useEffect, useState } from "react";
import DragIndicatiorRoundedIcon from "@mui/icons-material/DragIndicatorRounded"
import CloseRoundedIcon from "@mui/icons-material/CloseRounded"
import ZoomInRoundedIcon from "@mui/icons-material/ZoomInRounded"
import DeleteRoundedIcon from "@mui/icons-material/DeleteRounded"
import SortRoundedIcon from "@mui/icons-material/SortRounded"
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import QueryBuilderRoundedIcon from '@mui/icons-material/QueryBuilderRounded';
import Poster from "@/features/manga/components/ui/Poster";
import ZoomOutRoundedIcon from '@mui/icons-material/ZoomOutRounded';



export interface EditFile {
    uuid: string,
    previewLink: string,
    file?: File,
    name: string
}

export type UploadStatus = {
    state: "idle" | "queued" | "ready" | "error" | "uploading",
    progress?: number
}

function EditFileInput({
    onChange
}: {
    onChange: (value: EditFile[]) => void
}) {
    const handleDrop = (acceptedFiles: File[]) => {

        onChange(acceptedFiles.map((f: File) => ({
            uuid: v4(),
            previewLink: URL.createObjectURL(f),
            file: f,
            name: f.name
        } as EditFile)))
    }

    const {getRootProps, getInputProps} = useDropzone({
        onDrop: handleDrop,
        accept: {
            "image/jpeg": [".jpg", ".jpeg"],
            "image/png": [".png"],
            // "application/zip": [".zip"],
            // "application/x-zip-compressed": [".zip"]
        }
    })

    return (
        <>
            <Paper
                {...getRootProps()}
                elevation={1}
                sx={{
                    boxShadow: "none",
                    border: "solid 2px",
                    borderStyle: "dashed",
                    borderColor: "divider",
                    aspectRatio: "2/3",
                    borderRadius: "8px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    p: "5px 10px"
                }}
            >
                <UploadFileRoundedIcon 
                    sx={{
                        width: "42px",
                        height: "42px"
                    }}
                />
                <Typography
                    sx={{
                        mt: "10px",
                        textAlign: "center"
                    }}
                >
                    Нажмите или перенести файлы (.jpg, .png)
                </Typography>
            </Paper>
            <input {...getInputProps()} type="file" />
        </>
    )
}

function UploadStatusChip({
    state,
    progress,
}: {
    state: Exclude<UploadStatus["state"], "idle">
    progress?: number
}) {

    const statusContent = {
        "queued": {
            label: "В очереди",
            icon: <QueryBuilderRoundedIcon color="disabled" />
        },
        "ready": {
            label: "Готово",
            icon: <CheckCircleIcon color="success" />
        },
        "error": {
            label: "Ошибка",
            icon: <ErrorIcon color="error" />
        },
        "uploading": {
            label: "Загрузка",
            icon: (
                <CircularProgress
                    variant="determinate"
                    value={progress ?? 0}
                    color="primary"
                    size={"18px"}
                />
            )
        }
    }

    return (
        <Chip
            sx={{
                bgcolor: "background.paper",
            }}
            size="small"
            icon={statusContent[state].icon}
            label={statusContent[state].label}
        />
    )
}

function Zoomer({
    value,
    onChange
}: {
    value: number,
    onChange: (event: Event, value: number) => void
}) {

    const handleZoomButtons = () => {

    }

    useEffect(() => {

        document.addEventListener("keydown", handleZoomButtons)

        return () => {
            document.removeEventListener("keydown", handleZoomButtons)
        }
    }, [])
    
    return (
        <Box
            sx={{
                width: "240px",
                bgcolor: "background.paper",

                px: 2,
                py: 1,
                borderRadius: 4,

                display: "flex",
                flexDirection: "row",
                alignItems: "center"
            }}
        >
            <Stack direction="row" spacing={3} sx={{
                alignItems: "center",
                width: "100%"
            }}>
                <ZoomInRoundedIcon />
                <Slider value={value} onChange={onChange}/>
                <ZoomOutRoundedIcon />
            </Stack>
            <Typography
                sx={{
                    mx: 2,
                    minWidth: "34px"
                }}
            >
                {value}%
            </Typography>
        </Box>
    )
}

function EditFileZoomablePreview({
    open,
    url,
    onClose
}: {
    open: boolean,
    url: string | null,
    onClose: () => void
}) {
    const [zoomValue, setZoomValue] = useState(100)
    const [baseSize, setBaseSize] = useState<{ width: number; height: number } | null>(null);

    
    const scale = zoomValue / 100

    useEffect(() => {
        return () => {
            setZoomValue(100)
            setBaseSize(null)
        }
    }, [url])

    return (
        <Modal
            open={open}
            onClose={onClose}
            sx={{
                display: "flex",
                height: "100vh",

                overflowY: "auto"
            }}
        >
            <Box
                sx={{
                    mx: "auto"
                }}
            >
                {url && (
                    <img 
                        src={url}
                        style={{
                            display: "block",
                            width: baseSize ? `${baseSize.width * scale}px` : "auto",
                            height: baseSize ? `${baseSize.height * scale}px` : "auto",
                            transition: "width 0.1s ease, height 0.1s ease"
                        }}
                        onLoad={(e) => {
                            // Запоминаем размеры картинки при открытии (при 100%)
                            setBaseSize({
                                width: e.currentTarget.clientWidth,
                                height: e.currentTarget.clientHeight
                            });
                        }}
                    />
                )}
                <Box
                    sx={{
                        position: "fixed",
                        right: "15px",
                        bottom: "15px"
                    }}
                >
                    <Zoomer 
                        value={zoomValue}
                        onChange={(event, newValue) => setZoomValue(newValue)}
                    />
                </Box>
            </Box>
        </Modal>
    )
}

function EditFilePreview({
    file,
    onClose,
    onPreviewWithZoom,
    uploadStatus,
}: {
    file: EditFile,
    onClose: () => void,
    onPreviewWithZoom: () => void,
    uploadStatus?: UploadStatus,
}) {
    const hasPreview = typeof file.previewLink === "string" && Boolean(file.previewLink.trim())

    const {
        attributes, 
        listeners, 
        setNodeRef, 
        transform, 
        transition, 
        isDragging
    } = useSortable({ 
        id: file.uuid
    });

    return (
        <>
            <Box
                ref={setNodeRef} 
                {...attributes}
                sx={{
                    transform: CSS.Translate.toString(transform),
                    aspectRatio: "2/3",
                    zIndex: isDragging ? 10003 : 1,
                    position: "relative",
                    transition: transition
                }}
            >
                <Box 
                    sx={{
                        position: "relative",
                        width: "100%",
                        height: "100%",
                        borderRadius: "8px",
                        backgroundImage: hasPreview ? `url(${file.previewLink})` : undefined,
                        backgroundSize: "cover"
                    }}
                >
                    {!hasPreview && <Poster src="" />}
                    {uploadStatus && uploadStatus.state !== "idle" && (
                        <Box sx={{position: "absolute", left: 6, bottom: 6}}>
                            <UploadStatusChip state={uploadStatus.state} progress={uploadStatus.progress} />
                        </Box>
                    )}
                    <Box
                        sx={{
                            position: "absolute",
                            top: "5px",
                            right: "5px",
                            display: "flex",
                            flexDirection: "row",
                            columnGap: "5px"
                        }}
                    >
                        <DragIndicatiorRoundedIcon
                            {...listeners}  
                            sx={{
                                p: "2px",
                                backgroundColor: "background.paper",
                                borderRadius: "50%",
                                cursor: isDragging ? "grabbing" : "grab"
                            }}
                        />
                        <CloseRoundedIcon 
                            sx={{
                                p: "2px",
                                backgroundColor: "background.paper",
                                borderRadius: "50%",
                                cursor: "pointer"
                            }}
                            onClick={onClose}
                        />
                    </Box>
                    {hasPreview && <Box
                        sx={{
                            position: "absolute",
                            bottom: "5px",
                            right: "5px",

                            display: "flex"
                        }}
                    >
                        <ZoomInRoundedIcon 
                            onClick={() => onPreviewWithZoom?.()}
                            sx={{
                                p: "4px",
                                width: "32px",
                                height: "32px",
                                backgroundColor: "background.paper",
                                borderRadius: "50%",
                                cursor: "pointer"
                            }}
                        />
                    </Box>}
                </Box>  
                <Typography
                    sx={{
                        textOverflow: "ellipsis",
                        overflow: "hidden",
                        lineClamp: 2
                    }}
                >
                    {file.name}
                </Typography>
            </Box>
        </>
    )
}

export default function EditMultipleFilesInput({
    value,
    onChange,
    sx,
    uploadStatuses,
    onRetryUpload,
}: {
    value: EditFile[],
    onChange: (value: EditFile[]) => void,
    sx?: SxProps,
    uploadStatuses?: Record<string, UploadStatus>,
    onRetryUpload?: (uuid: string) => void,
}) {
    const items = value.map(file => file.uuid)

    const [zoomablePreviewURL, setZoomablePreviewURL] = useState<string | null>("")
    
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const onInputFile = (files: EditFile[]) => {
        const newVal = [...value, ...files]

        onChange(newVal)
    }

    function handleDragEnd(event: DragEndEvent) {
        const {active, over} = event;
        
        if (active.id !== over?.id) {
            const oldIndex = items.indexOf(active.id as string);
            const newIndex = items.indexOf(over?.id as string);

            if (oldIndex !== -1 && newIndex !== -1) {
                onChange(arrayMove(value, oldIndex, newIndex));
            }
        }
    }

    function handleDeleteFiles() {
        onChange([])
    }

    function handleSortFiles() {
        const oldValue = [...value]

        const newValue = oldValue.sort((fileA, fileB) => fileA.name?.localeCompare(fileB?.name))
        onChange(newValue)
    }

    return (
        <>
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    rowGap: 1,

                    ...sx
                }}
            >
                <Box
                    sx={{
                        display: "flex",
                        justifyContent: "end"
                    }}
                >
                    <Button
                        variant="text"
                        color="inherit"
                        endIcon={<SortRoundedIcon />}
                        onClick={handleSortFiles}
                    >
                        Упорядочить
                    </Button>
                    <Button
                        variant="text"
                        color="inherit"
                        endIcon={<DeleteRoundedIcon />}
                        onClick={handleDeleteFiles}
                    >
                        Очистить
                    </Button>
                </Box>
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                >
                    <Box
                        sx={{
                            border: "1px solid",
                            borderColor: "divider",
                            borderRadius: "12px",
                            p: "10px 14px",

                            display: "grid",
                            columnGap: "10px",
                            rowGap: "15px",
                            gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                        }}
                    >
                        <SortableContext 
                            items={items}
                        >
                            {value.map((v) => (
                                <EditFilePreview 
                                    key={v.uuid} 
                                    file={v}
                                    uploadStatus={uploadStatuses && (v.file
                                        ? uploadStatuses[v.uuid] ?? {state: "queued"}
                                        : {state: "idle"})}
                                    onPreviewWithZoom={() => {
                                        setZoomablePreviewURL(v.previewLink)
                                    }}
                                    onClose={() => {
                                        onChange(value.filter((f) => (f.uuid != v.uuid)))
                                    }}
                                />
                            ))}
                        </SortableContext>
                        <EditFileInput 
                            onChange={onInputFile}
                        />
                    </Box>
                </DndContext>
            </Box>
            <EditFileZoomablePreview 
                open={zoomablePreviewURL != null}
                url={zoomablePreviewURL}
                onClose={() => setZoomablePreviewURL(null)}
            />
        </>
    )
}
