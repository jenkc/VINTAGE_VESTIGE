import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '@/components/ui/Button'

describe('Button', () => {
    it('renders children', () => {
        render(<Button>Click me</Button>)
        expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
    })

    it('calls onClick when clicked', () => {
        const handler = vi.fn()
        render(<Button onClick={handler}>Click me</Button>)
        fireEvent.click(screen.getByRole('button'))
        expect(handler).toHaveBeenCalledOnce()
    })

    it('is disabled when disabled prop is set', () => {
        render(<Button disabled>Submit</Button>)
        expect(screen.getByRole('button')).toBeDisabled()
    })

    it('applies default variant classes', () => {
        render(<Button>Default</Button>)
        const btn = screen.getByRole('button')
        expect(btn.className).toContain('bg-accent')
    })

    it('applies outline variant classes', () => {
        render(<Button variant="outline">Outline</Button>)
        expect(screen.getByRole('button').className).toContain('border-2')
    })

    it('forwards ref', () => {
        const ref = { current: null }
        render(<Button ref={ref}>Ref test</Button>)
        expect(ref.current).not.toBeNull()
    })
})
