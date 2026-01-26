import { FormEvent, useState } from 'react';

interface RegisterFormProps {
  onSubmit: (email: string, firstName: string, lastName: string) => Promise<void>;
  onSwitchToLogin: () => void;
  isSubmitting?: boolean;
  error?: string | null;
  success?: string | null;
}

export default function RegisterForm({
  onSubmit,
  onSwitchToLogin,
  isSubmitting = false,
  error,
  success
}: RegisterFormProps) {
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(email.trim(), firstName.trim(), lastName.trim());
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-form__field">
        <label htmlFor="email">Email Address</label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          disabled={!!success}
        />
      </div>
      <div className="auth-form__field">
        <label htmlFor="firstName">First Name (optional)</label>
        <input
          id="firstName"
          name="firstName"
          type="text"
          autoComplete="given-name"
          value={firstName}
          onChange={(event) => setFirstName(event.target.value)}
          disabled={!!success}
        />
      </div>
      <div className="auth-form__field">
        <label htmlFor="lastName">Last Name (optional)</label>
        <input
          id="lastName"
          name="lastName"
          type="text"
          autoComplete="family-name"
          value={lastName}
          onChange={(event) => setLastName(event.target.value)}
          disabled={!!success}
        />
      </div>
      {error ? (
        <div className="auth-form__alert" role="alert">
          {error}
        </div>
      ) : null}
      {success ? (
        <div className="auth-form__success" role="status">
          {success}
        </div>
      ) : null}
      {!success ? (
        <button type="submit" className="auth-form__submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account...' : 'Create Account'}
        </button>
      ) : null}
      <div className="auth-form__switch">
        Already have an account?{' '}
        <button type="button" className="auth-form__switch-link" onClick={onSwitchToLogin}>
          Sign in
        </button>
      </div>
    </form>
  );
}
