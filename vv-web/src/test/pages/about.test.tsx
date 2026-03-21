import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import AboutPage from '@/app/about/page'

describe('About page', () => {
    it('renders the page heading', () => {
        render(<AboutPage />)
        expect(screen.getByRole('heading', { level: 1, name: 'Vintage Vestige' })).toBeInTheDocument()
    })

    it('shows the eyebrow label', () => {
        render(<AboutPage />)
        expect(screen.getByText('About')).toBeInTheDocument()
    })

    it('mentions the data sources', () => {
        render(<AboutPage />)
        expect(screen.getByText('The Metropolitan Museum of Art')).toBeInTheDocument()
        expect(screen.getByText('Smithsonian')).toBeInTheDocument()
        expect(screen.getByText('Fashionpedia')).toBeInTheDocument()
    })

    it('shows the Built With section', () => {
        render(<AboutPage />)
        expect(screen.getByText('Built With')).toBeInTheDocument()
    })
})
