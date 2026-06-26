import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import JobStatusBadge from '../JobStatusBadge';

describe('JobStatusBadge', () => {
  it('renders the shared status glyph contract for known statuses', () => {
    render(<JobStatusBadge status="completed" />);

    const badge = screen.getByLabelText('Completed');
    expect(badge).toHaveClass('job-status');
    expect(badge).toHaveAttribute('data-state', 'completed');
    expect(badge).toHaveTextContent('✅');
  });

  it('keeps custom glyphs and classes for sidebar derived states', () => {
    render(
      <JobStatusBadge
        status="running"
        glyph={{ icon: 'IMG', label: 'Waiting for images' }}
        label="Image generation 40% complete"
        className="sidebar-status"
      />
    );

    const badge = screen.getByLabelText('Image generation 40% complete');
    expect(badge).toHaveClass('job-status');
    expect(badge).toHaveClass('sidebar-status');
    expect(badge).toHaveAttribute('data-state', 'running');
    expect(badge).toHaveTextContent('IMG');
  });
});
