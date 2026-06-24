import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SidebarAdminLinks } from '../sidebar/SidebarAdminLinks';

const defaultProps = {
  adminUserManagementView: 'admin:users',
  adminReadingBedsView: 'admin:reading-beds',
  adminSettingsView: 'admin:settings',
  adminSystemView: 'admin:system'
} as const;

describe('SidebarAdminLinks', () => {
  it('routes admin buttons and marks the active view', () => {
    const handleSelectView = vi.fn();

    render(
      <SidebarAdminLinks
        {...defaultProps}
        selectedView="admin:system"
        onSelectView={handleSelectView}
      />
    );

    expect(screen.getByRole('button', { name: /System/i })).toHaveClass('is-active');

    fireEvent.click(screen.getByRole('button', { name: /User management/i }));
    fireEvent.click(screen.getByRole('button', { name: /Reading music/i }));
    fireEvent.click(screen.getByRole('button', { name: /^⚙️ Settings$/i }));
    fireEvent.click(screen.getByRole('button', { name: /System/i }));

    expect(handleSelectView.mock.calls).toEqual([
      ['admin:users'],
      ['admin:reading-beds'],
      ['admin:settings'],
      ['admin:system']
    ]);
  });

  it('keeps observability links external and token-free', () => {
    render(
      <SidebarAdminLinks
        {...defaultProps}
        selectedView="admin:users"
        onSelectView={vi.fn()}
      />
    );

    const grafana = screen.getByRole('link', { name: /Grafana/i });
    expect(grafana).toHaveAttribute('href', expect.stringContaining('grafana.langtools.fifosk.synology.me'));
    expect(grafana).toHaveAttribute('target', '_blank');
    expect(grafana).toHaveAttribute('rel', 'noopener noreferrer');
    expect(grafana.getAttribute('href')).not.toMatch(/token|auth/i);

    const prometheus = screen.getByRole('link', { name: /Prometheus/i });
    expect(prometheus).toHaveAttribute('href', 'https://prometheus.langtools.fifosk.synology.me/');
    expect(prometheus).toHaveAttribute('target', '_blank');
    expect(prometheus).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
