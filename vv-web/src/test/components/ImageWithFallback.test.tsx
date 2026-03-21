import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ImageWithFallback from '@/components/ui/ImageWithFallback'

describe('ImageWithFallback', () => {
    it('renders an img when src is provided', () => {
        render(<ImageWithFallback src="/test.jpg" alt="Test image" fill />)
        expect(screen.getByRole('img')).toBeInTheDocument()
    })

    it('shows gradient fallback when src is empty string', () => {
        const { container } = render(<ImageWithFallback src="" alt="No image" fill />)
        // Fallback is a div (not an <img> element) with role="img" and aria-label
        expect(container.querySelector('img')).toBeNull()
        expect(screen.getByLabelText('No image')).toBeInTheDocument()
    })

    it('shows gradient fallback after image load error', () => {
        const { container } = render(<ImageWithFallback src="/broken.jpg" alt="Broken" fill />)
        const img = container.querySelector('img')!
        fireEvent.error(img)
        // After error the <img> element is replaced by a fallback div
        expect(container.querySelector('img')).toBeNull()
        expect(screen.getByLabelText('Broken')).toBeInTheDocument()
    })

    it('passes className to the img', () => {
        render(<ImageWithFallback src="/test.jpg" alt="Styled" fill className="object-cover" />)
        expect(screen.getByRole('img').className).toContain('object-cover')
    })
})
