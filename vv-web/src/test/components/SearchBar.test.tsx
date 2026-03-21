import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import SearchBar from '@/components/search/SearchBar'

describe('SearchBar', () => {
    beforeEach(() => {
        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('renders with placeholder text', () => {
        render(<SearchBar onSearch={vi.fn()} placeholder="Search vintage..." />)
        expect(screen.getByPlaceholderText('Search vintage...')).toBeInTheDocument()
    })

    it('shows search icon when empty', () => {
        render(<SearchBar onSearch={vi.fn()} />)
        expect(screen.getByLabelText('Search')).toBeInTheDocument()
    })

    it('shows clear button when text is entered', () => {
        render(<SearchBar onSearch={vi.fn()} />)
        const input = screen.getByRole('textbox')
        fireEvent.change(input, { target: { value: 'dress' } })
        expect(screen.getByLabelText('Clear search')).toBeInTheDocument()
    })

    it('fires onSearch after 400ms debounce', () => {
        const onSearch = vi.fn()
        render(<SearchBar onSearch={onSearch} />)
        const input = screen.getByRole('textbox')

        fireEvent.change(input, { target: { value: 'silk' } })
        expect(onSearch).not.toHaveBeenCalled()

        vi.advanceTimersByTime(400)
        expect(onSearch).toHaveBeenCalledWith('silk')
    })

    it('fires onSearch immediately on Enter', () => {
        const onSearch = vi.fn()
        render(<SearchBar onSearch={onSearch} />)
        const input = screen.getByRole('textbox')

        fireEvent.change(input, { target: { value: 'velvet' } })
        fireEvent.keyDown(input, { key: 'Enter' })
        expect(onSearch).toHaveBeenCalledWith('velvet')
    })

    it('clears input and fires onSearch with empty string when X is clicked', () => {
        const onSearch = vi.fn()
        render(<SearchBar onSearch={onSearch} />)
        const input = screen.getByRole('textbox')

        fireEvent.change(input, { target: { value: 'coat' } })
        vi.advanceTimersByTime(400)

        fireEvent.click(screen.getByLabelText('Clear search'))

        expect((input as HTMLInputElement).value).toBe('')
        expect(onSearch).toHaveBeenLastCalledWith('')
    })
})
