import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Badge } from '@/components/ui/Badge'

describe('Badge', () => {
    it('renders children', () => {
        render(<Badge>1920s</Badge>)
        expect(screen.getByText('1920s')).toBeInTheDocument()
    })

    it('applies default variant classes', () => {
        render(<Badge>Default</Badge>)
        expect(screen.getByText('Default').className).toContain('bg-accent')
    })

    it('applies era variant classes', () => {
        render(<Badge variant="era">Victorian</Badge>)
        expect(screen.getByText('Victorian').className).toContain('bg-off-white')
    })

    it('applies outline variant classes', () => {
        render(<Badge variant="outline">Tag</Badge>)
        expect(screen.getByText('Tag').className).toContain('border-grey-200')
    })

    it('merges custom className', () => {
        render(<Badge className="text-[11px]">Small</Badge>)
        expect(screen.getByText('Small').className).toContain('text-[11px]')
    })
})
