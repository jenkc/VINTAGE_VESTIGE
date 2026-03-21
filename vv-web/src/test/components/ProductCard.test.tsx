import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ProductCard from '@/components/search/ProductCard'
import type { SearchResult } from '@/types'

const baseProduct: SearchResult = {
    id: 1,
    score: 0.91,
    platform: 'met_museum',
    title: 'Silk Evening Gown',
    category: 'dress',
    primary_image: '/gown.jpg',
    era: '1920s',
    decade: '1920s',
    style_tags: ['Art Deco', 'beaded'],
    colors: ['gold', 'black'],
    material: 'silk',
    garment_type: 'dress',
    vibe: 'glamorous',
    fit_style: 'fitted',
    occasion: 'formal',
    ai_description: 'A stunning silk gown.',
    culture: 'American',
    object_date: '1925',
    price: null,
}

describe('ProductCard', () => {
    it('renders the product title', () => {
        render(<ProductCard product={baseProduct} />)
        expect(screen.getByText('Silk Evening Gown')).toBeInTheDocument()
    })

    it('links to the product page', () => {
        render(<ProductCard product={baseProduct} />)
        expect(screen.getByRole('link')).toHaveAttribute('href', '/product/1')
    })

    it('renders the era badge', () => {
        render(<ProductCard product={baseProduct} />)
        expect(screen.getByText('1920s')).toBeInTheDocument()
    })

    it('shows match score when product has score', () => {
        render(<ProductCard product={baseProduct} />)
        expect(screen.getByText('91%')).toBeInTheDocument()
    })

    it('shows explicit score prop over product.score', () => {
        render(<ProductCard product={baseProduct} score={0.75} />)
        expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('shows platform name badge', () => {
        render(<ProductCard product={baseProduct} />)
        expect(screen.getByText('The Met')).toBeInTheDocument()
    })

    it('shows "No image" placeholder when primary_image is null', () => {
        render(<ProductCard product={{ ...baseProduct, primary_image: null }} />)
        expect(screen.getByText('No image')).toBeInTheDocument()
    })

    it('does not show era badge when era is null', () => {
        render(<ProductCard product={{ ...baseProduct, era: null }} />)
        expect(screen.queryByText('1920s')).toBeNull()
    })
})
