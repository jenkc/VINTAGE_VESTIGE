import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ScoreCircle from '@/components/bridge/ScoreCircle'

describe('ScoreCircle', () => {
    it('displays percent as integer', () => {
        render(<ScoreCircle score={0.87} />)
        expect(screen.getByText('87')).toBeInTheDocument()
    })

    it('displays "match" label', () => {
        render(<ScoreCircle score={0.5} />)
        expect(screen.getByText('match')).toBeInTheDocument()
    })

    it('has accessible role and aria-label', () => {
        render(<ScoreCircle score={0.72} />)
        expect(screen.getByRole('img', { name: '72% match score' })).toBeInTheDocument()
    })

    it('rounds score correctly', () => {
        render(<ScoreCircle score={0.755} />)
        expect(screen.getByText('76')).toBeInTheDocument()
    })
})
