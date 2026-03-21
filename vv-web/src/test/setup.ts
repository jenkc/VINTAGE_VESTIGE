import '@testing-library/jest-dom'
import React from 'react'
import { vi } from 'vitest'

vi.mock('next/image', () => ({
    default: ({ src, alt, fill, className, sizes, onError, ...rest }: Record<string, unknown>) =>
        React.createElement('img', { src, alt, className, 'data-fill': fill, sizes, onError, ...rest })
}))

vi.mock('next/link', () => ({
    default: ({ href, children, className, ...rest }: { href: string; children: React.ReactNode; className?: string; [key: string]: unknown }) =>
        React.createElement('a', { href, className, ...rest }, children)
}))