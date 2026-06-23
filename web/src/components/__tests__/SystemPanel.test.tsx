import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import SystemPanel from '../admin/SystemPanel';
import { fetchAuditLog, fetchSystemStatus } from '../../api/client';
import type { AuditLogResponse, SystemStatusResponse } from '../../api/client';

vi.mock('../../api/client', () => ({
  fetchAuditLog: vi.fn(),
  fetchSystemStatus: vi.fn(),
  reloadConfig: vi.fn(),
  requestRestart: vi.fn(),
  cancelRestart: vi.fn()
}));

const statusPayload: SystemStatusResponse = {
  uptimeSeconds: 120,
  configLoadedAt: '2026-06-23T12:00:00Z',
  activeSnapshotId: undefined,
  dbEnabled: true,
  configDbPath: '/tmp/config.db',
  libraryDbPath: '/tmp/library.db',
  pendingChanges: false,
  restartRequired: false,
  restartKeys: [],
  queuePressure: {
    acceptingJobs: true,
    isUnderPressure: true,
    queueDepth: 2,
    activeCount: 1,
    softLimit: 2,
    hardLimit: 5,
    rejectionCount: 0,
    delayCount: 1
  }
};

const auditPayload: AuditLogResponse = {
  entries: [],
  total: 0,
  limit: 20,
  offset: 0
};

describe('SystemPanel', () => {
  const fetchSystemStatusMock = vi.mocked(fetchSystemStatus);
  const fetchAuditLogMock = vi.mocked(fetchAuditLog);

  beforeEach(() => {
    vi.clearAllMocks();
    fetchSystemStatusMock.mockResolvedValue(statusPayload);
    fetchAuditLogMock.mockResolvedValue(auditPayload);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders backend queue pressure status for admins', async () => {
    render(<SystemPanel currentUser="admin" />);

    expect(await screen.findByText('Delaying submissions')).toBeInTheDocument();
    expect(screen.getByText('2 / 5')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('Queue Pressure')).toBeInTheDocument();
    expect(screen.getByText(/soft limit of 2/i)).toBeInTheDocument();

    await waitFor(() => expect(fetchSystemStatusMock).toHaveBeenCalledTimes(1));
    expect(fetchAuditLogMock).toHaveBeenCalledWith({ limit: 20 });
  });
});
