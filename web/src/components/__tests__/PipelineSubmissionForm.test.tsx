import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PipelineRequestPayload } from '../../api/dtos';
import { PipelineSubmissionForm } from '../PipelineSubmissionForm';

describe('PipelineSubmissionForm', () => {
  it('submits normalized payloads when valid', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[], Promise<void>>().mockResolvedValue();

    render(<PipelineSubmissionForm onSubmit={handleSubmit} />);

    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.type(screen.getByLabelText(/Base output file/i), 'output');
    await user.type(screen.getByLabelText(/Target languages/i), 'es,fr');
    await user.clear(screen.getByLabelText(/Config overrides/i));
    await user.type(screen.getByLabelText(/Config overrides/i), '{"debug":true}');
    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalled());

    const payload = handleSubmit.mock.calls[0][0] as PipelineRequestPayload;
    expect(payload.inputs.target_languages).toEqual(['es', 'fr']);
    expect(payload.config).toEqual({ debug: true });
    expect(payload.inputs.generate_audio).toBe(true);
  });

  it('shows an error when JSON input cannot be parsed', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<PipelineSubmissionForm onSubmit={handleSubmit} />);

    await user.clear(screen.getByLabelText(/Config overrides/i));
    await user.type(screen.getByLabelText(/Config overrides/i), '{broken');
    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid json/i);
    expect(handleSubmit).not.toHaveBeenCalled();
  });
});
