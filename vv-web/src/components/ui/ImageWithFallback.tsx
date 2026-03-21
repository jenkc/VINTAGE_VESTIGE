"use client";

import { useState } from "react";
import Image, { ImageProps } from "next/image";
import { cn } from "@/lib/utils";

export default function ImageWithFallback({ className, alt, ...props }: ImageProps) {
    const [error, setError] = useState(false);

    if (error || !props.src) {
        return (
            <div
                className={cn(
                    "bg-gradient-to-br from-grey-100 to-grey-200",
                    className
                )}
                role="img"
                aria-label={alt}
            />
        )
    }

    return (
        <Image
            className={className}
            alt={alt}
            onError={() => setError(true)}
            {...props}
        />
    );
}