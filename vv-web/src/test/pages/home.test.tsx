import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import HomePage from '@/app/page'

vi.mock('@/lib/api', () => ({
    getTopBridges: vi.fn().mockResolvedValue({ bridges: [] }),
}))

vi.mock('@/components/bridge', () => ({
    BridgeCardCompact: ({ bridge }: { bridge: { id: number } }) => (
        <div data-testid={`bridge-${bridge.id}`} />
    ),
}))

describe('Home page', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders the hero heading', async () => {
        render(await HomePage())
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
            'A fashion knowledge graph connecting 500 years of design history'
        )
    })

    it('renders the Vintage Vestige eyebrow', async () => {
        render(await HomePage())
        expect(screen.getByText('Vintage Vestige')).toBeInTheDocument()
    })

    it('has a Start Searching link to /search', async () => {
        render(await HomePage())
        const link = screen.getByRole('link', { name: 'Start Searching' })
        expect(link).toHaveAttribute('href', '/search')
    })

    it('has an Upload Image link', async () => {
        render(await HomePage())
        const link = screen.getByRole('link', { name: 'Upload Image' })
        expect(link).toHaveAttribute('href', '/search?mode=image')
    })

    it('renders the How It Works section', async () => {
        render(await HomePage())
        expect(screen.getByRole('heading', { name: 'How It Works' })).toBeInTheDocument()
        expect(screen.getByText('AI Style Analysis')).toBeInTheDocument()
        expect(screen.getByText('Multi-Modal Search')).toBeInTheDocument()
        expect(screen.getByText('Style Bridges')).toBeInTheDocument()
    })

    it('renders the Featured Bridges region', async () => {
        render(await HomePage())
        expect(screen.getByRole('region', { name: 'Featured style bridges' })).toBeInTheDocument()
    })
})
