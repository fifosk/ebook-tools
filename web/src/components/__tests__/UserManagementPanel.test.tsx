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
  suspendUserAccount,
  updateUserProfile
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
  const updateProfileMock = vi.mocked(updateUserProfile);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a new user and refreshes the listing', async () => {
    const user = userEvent.setup();
    let users: ManagedUser[] = [
      {
        username: 'alice',
        roles: ['admin'],
        status: 'active',
        metadata: {},
        email: 'alice@example.com',
        first_name: 'Alice',
        last_name: 'Admin'
      }
    ];

    listUsersMock.mockImplementation(async () => users);
    createUserMock.mockImplementation(async (payload) => {
      const created: ManagedUser = {
        username: payload.username,
        roles: payload.roles,
        status: 'active',
        metadata: {},
        email: payload.email ?? null,
        first_name: payload.first_name ?? null,
        last_name: payload.last_name ?? null
      };
      users = [...users, created];
      return created;
    });

    render(<UserManagementPanel currentUser="alice" />);

    expect(await screen.findByText('alice')).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Username/i), 'bob');
    await user.type(screen.getByLabelText(/Email address/i), 'bob@example.com');
    await user.type(screen.getByLabelText(/^First name/i), 'Bob');
    await user.type(screen.getByLabelText(/Last name/i), 'Builder');
    await user.type(screen.getByLabelText(/Temporary password/i), 'secretpass!');
    await user.selectOptions(screen.getByLabelText(/Role/i), 'standard_user');
    await user.click(screen.getByRole('button', { name: /Create user/i }));

    await waitFor(() =>
      expect(createUserMock).toHaveBeenCalledWith({
        username: 'bob',
        password: 'secretpass!',
        roles: ['standard_user'],
        email: 'bob@example.com',
        first_name: 'Bob',
        last_name: 'Builder'
      })
    );

    expect(await screen.findByText('bob')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/created user 'bob'/i);
  });

  it('manages suspension, password resets, and deletion', async () => {
    const user = userEvent.setup();
    let users: ManagedUser[] = [
      {
        username: 'alice',
        roles: ['admin'],
        status: 'active',
        metadata: {},
        email: 'alice@example.com',
        first_name: 'Alice',
        last_name: 'Admin'
      },
      {
        username: 'bob',
        roles: ['standard_user'],
        status: 'active',
        metadata: {},
        email: 'bob@example.com',
        first_name: 'Bob',
        last_name: 'Builder'
      }
    ];

    listUsersMock.mockImplementation(async () => users);
    updateProfileMock.mockImplementation(async (username, payload) => {
      users = users.map((record) =>
        record.username === username
          ? {
              ...record,
              email: payload.email ?? null,
              first_name: payload.first_name ?? null,
              last_name: payload.last_name ?? null
            }
          : record
      );
      return users.find((record) => record.username === username)!;
    });
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

  it('updates profile metadata for an existing user', async () => {
    const user = userEvent.setup();
    let users: ManagedUser[] = [
      {
        username: 'alice',
        roles: ['admin'],
        status: 'active',
        metadata: {},
        email: 'alice@example.com',
        first_name: 'Alice',
        last_name: 'Admin'
      },
      {
        username: 'bob',
        roles: ['standard_user'],
        status: 'active',
        metadata: {},
        email: 'bob@example.com',
        first_name: 'Bob',
        last_name: 'Builder'
      }
    ];

    listUsersMock.mockImplementation(async () => users);
    updateProfileMock.mockImplementation(async (username, payload) => {
      users = users.map((record) =>
        record.username === username
          ? {
              ...record,
              email: payload.email ?? null,
              first_name: payload.first_name ?? null,
              last_name: payload.last_name ?? null
            }
          : record
      );
      return users.find((record) => record.username === username)!;
    });

    render(<UserManagementPanel currentUser="alice" />);

    const bobRow = await screen.findByRole('row', { name: /bob/i });

    await user.click(within(bobRow).getByRole('button', { name: /Edit profile/i }));

    const profileForm = await screen.findByRole('form', { name: /Edit profile for bob/i });
    const emailField = within(profileForm).getByLabelText(/Email address/i);
    const firstNameField = within(profileForm).getByLabelText(/First name/i);
    const lastNameField = within(profileForm).getByLabelText(/Last name/i);

    await user.clear(emailField);
    await user.type(emailField, 'bob.updated@example.com');
    await user.clear(firstNameField);
    await user.type(firstNameField, 'Robert');
    await user.clear(lastNameField);
    await user.type(lastNameField, 'Builder');

    await user.click(within(profileForm).getByRole('button', { name: /Save bob/i }));

    await waitFor(() =>
      expect(updateProfileMock).toHaveBeenCalledWith('bob', {
        email: 'bob.updated@example.com',
        first_name: 'Robert',
        last_name: 'Builder'
      })
    );

    expect(await screen.findByText('bob.updated@example.com')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/updated profile for 'bob'/i);
  });
});
