import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetKeys?: unknown[];
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component that catches React errors in child components.
 *
 * Features:
 * - Custom fallback UI
 * - Error logging callback
 * - Auto-reset on resetKeys change (e.g., when navigating to different job)
 * - Manual retry button
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary
 *   fallback={<CustomErrorUI />}
 *   onError={(error, errorInfo) => logToSentry(error, errorInfo)}
 *   resetKeys={[jobId]}
 * >
 *   <JobProgress jobId={jobId} />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  componentDidUpdate(prevProps: Props) {
    // Auto-reset when resetKeys change (e.g., navigating to different job)
    if (
      this.state.hasError &&
      prevProps.resetKeys !== this.props.resetKeys
    ) {
      this.setState({ hasError: false, error: null });
    }
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div
          className="error-boundary-fallback"
          role="alert"
          style={{
            padding: '2rem',
            margin: '2rem',
            border: '2px solid #ef4444',
            borderRadius: '0.5rem',
            backgroundColor: '#fef2f2',
          }}
        >
          <h3 style={{ margin: '0 0 1rem 0', color: '#dc2626' }}>
            Something went wrong
          </h3>
          <p style={{ margin: '0 0 1rem 0', color: '#991b1b' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <details style={{ marginBottom: '1rem' }}>
            <summary
              style={{
                cursor: 'pointer',
                color: '#7c2d12',
                userSelect: 'none',
              }}
            >
              Error details
            </summary>
            <pre
              style={{
                marginTop: '0.5rem',
                padding: '0.5rem',
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '0.25rem',
                overflow: 'auto',
                fontSize: '0.875rem',
              }}
            >
              {this.state.error?.stack || 'No stack trace available'}
            </pre>
          </details>
          <button
            onClick={this.handleRetry}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#dc2626',
              color: '#fff',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '500',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = '#b91c1c';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = '#dc2626';
            }}
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
