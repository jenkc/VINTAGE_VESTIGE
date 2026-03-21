import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SearchPage from '@/app/search/page'
import type { SearchResponse } from '@/types'

const mockPush = vi.fn()
const mockReplace = vi.fn()
const mockGet = vi.fn()

vi.mock('next/navigation', () => ({
    useSearchParams: () => ({ get: mockGet }),
    useRouter: () => ({ push: mockPush, replace: mockReplace }),
}))

vi.mock('@/lib/api', () => ({
    searchByText: vi.fn(),
}))

import { searchByText } from '@/lib/api'

const mockSearchByText = vi.mocked(searchByText)

const sampleResults: SearchResponse = {
    query: 'silk',
    total: 1,
    results: [
        {
            id: 42,
            score: 0.9,
            platform: 'met_museum',
            title: 'Silk Robe',
            category: 'top',
            primary_image: null,
            era: '1900s',
            decade: '1900s',
            style_tags: [],
            colors: [],
            material: 'silk',
            garment_type: 'robe',
            vibe: null,
            fit_style: null,
            occasion: null,
            ai_description: null,
            culture: null,
            object_date: null,
            price: null,
        },
    ],
}

describe('Search page', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        mockGet.mockReturnValue(null)
        mockSearchByText.mockResolvedValue(sampleResults)
    })

    it('renders the search form', () => {
        render(<SearchPage />)
        expect(screen.getByRole('search', { name: 'Search garments' })).toBeInTheDocument()
    })

    it('renders the search input with placeholder', () => {
        render(<SearchPage />)
        expect(
            screen.getByPlaceholderText('Search by style, era, or description...')
        ).toBeInTheDocument()
    })

    it('renders submit button', () => {
        render(<SearchPage />)
        expect(screen.getByRole('button', { name: 'Submit search' })).toBeInTheDocument()
    })

    it('does not show results before a search', () => {
        render(<SearchPage />)
        expect(screen.queryByText('Search Results')).toBeNull()
    })

    it('calls searchByText and shows results after form submit', async () => {
        render(<SearchPage />)
        const input = screen.getByPlaceholderText('Search by style, era, or description...')

        fireEvent.change(input, { target: { value: 'silk' } })
        fireEvent.submit(screen.getByRole('search'))

        await waitFor(() => {
            expect(mockSearchByText).toHaveBeenCalledWith('silk', undefined, expect.any(Number))
        })
        await waitFor(() => {
            expect(screen.getByText('Silk Robe')).toBeInTheDocument()
        })
    })

    it('shows empty state when no results returned', async () => {
        mockSearchByText.mockResolvedValueOnce({ query: 'xyz', total: 0, results: [] })

        render(<SearchPage />)
        const input = screen.getByPlaceholderText('Search by style, era, or description...')

        fireEvent.change(input, { target: { value: 'xyz' } })
        fireEvent.submit(screen.getByRole('search'))

        await waitFor(() => {
            expect(screen.getByText('No results found. Try a different search term.')).toBeInTheDocument()
        })
    })

    it('shows error message when API call fails', async () => {
        mockSearchByText.mockRejectedValueOnce(new Error('Network error'))

        render(<SearchPage />)
        const input = screen.getByPlaceholderText('Search by style, era, or description...')

        fireEvent.change(input, { target: { value: 'velvet' } })
        fireEvent.submit(screen.getByRole('search'))

        await waitFor(() => {
            expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument()
        })
    })

    it('pre-fills query from URL param and runs search on load', async () => {
        mockGet.mockReturnValue('velvet')

        render(<SearchPage />)

        await waitFor(() => {
            expect(mockSearchByText).toHaveBeenCalledWith('velvet', undefined, expect.any(Number))
        })
    })
})
