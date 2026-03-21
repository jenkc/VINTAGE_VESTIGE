import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import BridgeCardCompact from '@/components/bridge/BridgeCardCompact'
import type { BridgeResult, ProductSummary } from '@/types'

vi.mock('@/components/bridge/BridgeConnector', () => ({
    default: () => <div data-testid="bridge-connector" />,
}))
vi.mock('@/components/bridge/ConnectionBadge', () => ({
    default: () => <div data-testid="connection-badge" />,
}))
vi.mock('@/components/bridge/AttributePill', () => ({
    default: ({ label, value }: { label: string; value: string }) => (
        <span data-testid="attribute-pill">{label}: {value}</span>
    ),
}))

const sourceSummary = {
    id: 10,
    platform: 'met_museum',
    title: 'Victorian Bodice',
    display_title: null,
    primary_image: '/bodice.jpg',
    era: '1880s',
    decade: '1880s',
    fp_category: 'top',
    silhouette: 'fitted',
    material: 'silk',
    culture: 'British',
    ai_description: null,
    style_tags: [],
    colors: [],
    vibe_scores: null,
    designer: null,
    named_movements: [],
    influence_references: [],
    production_mode: null,
}

const targetSummary: ProductSummary = {
    id: 20,
    platform: 'va_museum',
    title: 'Modern Corset Top',
    display_title: null,
    primary_image: '/corset.jpg',
    era: '2010s',
    decade: '2010s',
    fp_category: 'top',
    silhouette: 'fitted',
    material: 'leather',
    culture: 'British',
    ai_description: null,
    style_tags: [],
    colors: [],
    vibe_scores: null,
    designer: null,
    named_movements: [],
    influence_references: [],
    production_mode: null,
}

const bridge: BridgeResult = {
    id: 1,
    source: sourceSummary,
    target: targetSummary,
    bridge_score: 0.84,
    entity_score: 15.2,
    text_similarity: 0.8,
    image_similarity: 0.75,
    bridge_narrative: 'The fitted silhouette echoes across a century of fashion.',
    shared_entities: {
        construction_technique: ['tailoring'],
        named_movements: ['Minimalism'],
    },
    created_at: '2026-01-01T00:00:00Z',
    crossing_type: 'cross_culture',
    connection_mode: 'shared_entity',
    year_gap: 130,
    directed: false,
}

describe('BridgeCardCompact', () => {
    it('links to the source product page', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getByRole('link')).toHaveAttribute('href', '/product/10')
    })

    it('shows era row with source and target eras', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getByText('1880s → 2010s')).toBeInTheDocument()
    })

    it('shows bridge score as percentage', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getByText('84%')).toBeInTheDocument()
    })

    it('renders bridge narrative', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getByText(/echoes across a century/)).toBeInTheDocument()
    })

    it('renders attribute pills for shared attributes', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getAllByTestId('attribute-pill').length).toBeGreaterThan(0)
    })

    it('renders connection badge when connection_mode is set', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getByTestId('connection-badge')).toBeInTheDocument()
    })

    it('renders the bridge connector', () => {
        render(<BridgeCardCompact bridge={bridge} />)
        expect(screen.getByTestId('bridge-connector')).toBeInTheDocument()
    })

    it('handles missing narrative gracefully', () => {
        render(<BridgeCardCompact bridge={{ ...bridge, bridge_narrative: null }} />)
        expect(screen.queryByText(/echoes/)).toBeNull()
    })
})
