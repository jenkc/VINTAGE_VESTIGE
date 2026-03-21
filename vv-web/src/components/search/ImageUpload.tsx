"use client";

import { useState, useRef, useCallback } from "react";
import { Camera, X, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface ImageUploadProps {
    onImageSelect: (base64: string) => void;
    onClear: () => void;
    className?: string;
}

export default function ImageUpload({
    onImageSelect,
    onClear,
    className,
}: ImageUploadProps) {
    const [preview, setPreview] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const processFile = useCallback(
        (file: File) => {
            if (!file.type.startsWith("image/")) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                const base64 = e.target?.result as string;
                setPreview(base64);
                onImageSelect(base64);
            };
            reader.readAsDataURL(file);
        },
        [onImageSelect]
    );

    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (file) processFile(file);
    }

    function handleDrop(e: React.DragEvent) {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) processFile(file);
    }

    function handleDragOver(e: React.DragEvent) {
        e.preventDefault();
        setIsDragging(true);
    }

    function handleDragLeave() {
        setIsDragging(false);
    }

    function handleClear() {
        setPreview(null);
        if (inputRef.current) inputRef.current.value = "";
        onClear();
    }

    // -- Preview state ---------------------------------------------
    if (preview) {
        return (
            <div className={cn("relative w-full max-w-[400px]", className)}>
                <img
                    src={preview}
                    alt="Upload preview"
                    className="w-full border border-grey-200 object-cover"
                />
                <button
                    onClick={handleClear}
                    className="absolute right-2 top-2 rounded-full bg-black/70 p-1.5 text-white hover:bg-black"
                    aria-label="Remove image"
                >
                    <X size={16} />
                </button>
            </div>
        );
    }

    // -- Drop zone state ---------------------------------------------
    return (
        <div className={cn("w-full max-w-[400px]", className)}>
            <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                className={cn(
                    "flex w-full flex-col items-center gap-3 border-2 border-dashed p-8",
                    "transition-colors duration-200 cursor-pointer",
                    isDragging
                        ? "border-accent bg-accent/5"
                        : "border-grey-200 hover:border-grey-400"
                )}
            >
                {/* Mobile: camera icon, Desktop: upload icon */}
                <Camera size={28} className="text-grey-400 md:hidden" />
                <Upload size={28} className="text-grey-400 hidden md:block" />

                <span className="text-sm text-grey-400 md:hidden">
                    Take photo or upload
                </span>
                <span className="text-sm text-grey-400 hidden md:block">
                    Drop an image here or click to upload
                </span>
            </button>

            <input
                ref={inputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
            />
        </div>
    );
}
