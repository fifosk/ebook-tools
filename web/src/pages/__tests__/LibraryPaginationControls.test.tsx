import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import LibraryPaginationControls from '../library/LibraryPaginationControls';

describe('LibraryPaginationControls', () => {
  it('renders the range label and disables previous on the first page', () => {
    const onPageChange = vi.fn();
    render(
      <LibraryPaginationControls
        page={1}
        totalPages={4}
        rangeLabel="Showing 1-20 of 80"
        onPageChange={onPageChange}
      />,
    );

    const nav = screen.getByRole('navigation', { name: 'Library pagination' });

    expect(within(nav).getByText('Showing 1-20 of 80')).toBeInTheDocument();
    expect(within(nav).getByRole('button', { name: 'Previous' })).toBeDisabled();

    fireEvent.click(within(nav).getByRole('button', { name: 'Next' }));

    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('disables next on the last page and routes previous', () => {
    const onPageChange = vi.fn();
    render(
      <LibraryPaginationControls
        page={4}
        totalPages={4}
        rangeLabel="Showing 61-80 of 80"
        onPageChange={onPageChange}
      />,
    );

    const nav = screen.getByRole('navigation', { name: 'Library pagination' });

    expect(within(nav).getByRole('button', { name: 'Next' })).toBeDisabled();

    fireEvent.click(within(nav).getByRole('button', { name: 'Previous' }));

    expect(onPageChange).toHaveBeenCalledWith(3);
  });
});
