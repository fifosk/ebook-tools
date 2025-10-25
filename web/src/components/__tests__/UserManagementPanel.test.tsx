import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import UserManagementPanel from '../admin/UserManagementPanel';
import {
  activateUserAccount,
  createUser,
  deleteUserAccount,
  listUsers,
  resetUserPassword,
  suspendUserAccount
} from '../../api/client';
import type { ManagedUser } from '../../api/dtos';

vi.mock('../../api/client');

describe('UserManagementPanel', () => {
  const listUsersMock = vi.mocked(listUsers);
  const createUserMock = vi.mocked(createUser);
  const suspendUserMock = vi.mocked(suspendUserAccount);
  const activateUserMock = vi.mocked(activateUserAccount);
  const deleteUserMock = vi.mocked(deleteUserAccount);
  const resetPasswordMock = vi.mocked(resetUserPassword);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a new user and refreshes the listing', async () => {
    const user = userEvent.setup();
    let users: ManagedUser[] = [
      { username: 'alice', roles: ['admin'], status: 'active', metadata: {} }
    ];

    listUsersMock.mockImplementation(async () => users);
    createUserMock.mockImplementation(async (payload) => {
      const created: ManagedUser = {
        username: payload.username,
        roles: payload.roles,
        status: 'active',
        metadata: {}
      };
      users = [...users, created];
      return created;
    });

    render(<UserManagementPanel currentUser="alice" />);

    expect(await screen.findByText('alice')).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Username/i), 'bob');
    await user.type(screen.getByLabelText(/Temporary password/i), 'secretpass!');
    await user.selectOptions(screen.getByLabelText(/Role/i), 'standard_user');
    await user.click(screen.getByRole('button', { name: /Create user/i }));

    await waitFor(() =>
      expect(createUserMock).toHaveBeenCalledWith({
        username: 'bob',
        password: 'secretpass!',
        roles: ['standard_user']
      })
    );

    expect(await screen.findByText('bob')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/created user 'bob'/i);
  });

  it('manages suspension, password resets, and deletion', async () => {
    const user = userEvent.setup();
    let users: ManagedUser[] = [
      { username: 'alice', roles: ['admin'], status: 'active', metadata: {} },
      { username: 'bob', roles: ['standard_user'], status: 'active', metadata: {} }
    ];

    listUsersMock.mockImplementation(async () => users);
    suspendUserMock.mockImplementation(async (username) => {
      users = users.map((record) =>
        record.username === username ? { ...record, status: 'suspended' } : record
      );
      return users.find((record) => record.username === username)!;
    });
    activateUserMock.mockImplementation(async (username) => {
      users = users.map((record) =>
        record.username === username ? { ...record, status: 'active' } : record
      );
      return users.find((record) => record.username === username)!;
    });
    deleteUserMock.mockImplementation(async (username) => {
      users = users.filter((record) => record.username !== username);
    });
    resetPasswordMock.mockResolvedValue();

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('updatedPass1!');

    render(<UserManagementPanel currentUser="alice" />);

    const bobRow = await screen.findByRole('row', { name: /bob/i });
    expect(within(bobRow).getByText(/Active/i)).toBeInTheDocument();

    await user.click(within(bobRow).getByRole('button', { name: /Suspend/i }));
    await waitFor(() => expect(suspendUserMock).toHaveBeenCalledWith('bob'));
    await waitFor(() => expect(within(bobRow).getByText(/Suspended/i)).toBeInTheDocument());

    await user.click(within(bobRow).getByRole('button', { name: /Activate/i }));
    await waitFor(() => expect(activateUserMock).toHaveBeenCalledWith('bob'));
    await waitFor(() => expect(within(bobRow).getByText(/Active/i)).toBeInTheDocument());

    await user.click(within(bobRow).getByRole('button', { name: /Reset password/i }));
    await waitFor(() =>
      expect(resetPasswordMock).toHaveBeenCalledWith('bob', { password: 'updatedPass1!' })
    );

    await user.click(within(bobRow).getByRole('button', { name: /Delete/i }));
    await waitFor(() => expect(deleteUserMock).toHaveBeenCalledWith('bob'));
    await waitFor(() => expect(screen.queryByText('bob')).not.toBeInTheDocument());

    confirmSpy.mockRestore();
    promptSpy.mockRestore();
  });
});
