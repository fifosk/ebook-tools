import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PipelineRequestPayload } from '../../api/dtos';
import { PipelineSubmissionForm } from '../PipelineSubmissionForm';

describe('PipelineSubmissionForm', () => {
  it('submits normalized payloads when valid', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();

    render(<PipelineSubmissionForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.type(screen.getByLabelText(/Base output file/i), 'output');
    await user.clear(screen.getByLabelText(/Input language/i));
    await user.type(screen.getByLabelText(/Input language/i), 'English');

    await user.click(screen.getByRole('checkbox', { name: 'French' }));
    await user.click(screen.getByRole('checkbox', { name: 'German' }));

    fireEvent.change(screen.getByLabelText(/Config overrides JSON/i), {
      target: { value: '{"debug":true}' }
    });

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalled());

    const firstCall = handleSubmit.mock.calls[0];
    expect(firstCall).toBeDefined();
    if (!firstCall) {
      throw new Error('Expected the form submission handler to receive a payload');
    }
    const [payload] = firstCall;
    expect(payload.inputs.target_languages).toEqual(['French', 'German']);
    expect(payload.config).toEqual({ debug: true });
    expect(payload.inputs.generate_audio).toBe(true);
  });

  it('shows an error when JSON input cannot be parsed', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<PipelineSubmissionForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.type(screen.getByLabelText(/Base output file/i), 'output');
    await user.clear(screen.getByLabelText(/Input language/i));
    await user.type(screen.getByLabelText(/Input language/i), 'English');
    await user.click(screen.getByRole('checkbox', { name: 'French' }));

    fireEvent.change(screen.getByLabelText(/Config overrides JSON/i), {
      target: { value: '{broken' }
    });

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid json/i);
    expect(handleSubmit).not.toHaveBeenCalled();
  });
});
