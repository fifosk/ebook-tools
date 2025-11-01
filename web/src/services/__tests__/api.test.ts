import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { subscribeToJobEvents } from '../api';
import { ProgressEventPayload } from '../../api/dtos';

const buildEventStreamUrlMock = vi.hoisted(() => vi.fn<[string], string>());

vi.mock('../../api/client', () => ({
  buildEventStreamUrl: buildEventStreamUrlMock
}));

class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  options?: EventSourceInit;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;

  constructor(url: string, options?: EventSourceInit) {
    this.url = url;
    this.options = options;
    MockEventSource.instances.push(this);
  }

  emitMessage(data: string): void {
    const event = new MessageEvent<string>('message', { data });
    this.onmessage?.(event);
  }

  emitError(event: Event = new Event('error')): void {
    this.onerror?.(event);
  }

  close(): void {
    this.closed = true;
  }
}

describe('subscribeToJobEvents', () => {
  let originalWindowEventSource: typeof EventSource | undefined;
  let originalGlobalEventSource: typeof EventSource | undefined;

  beforeAll(() => {
    originalWindowEventSource = window.EventSource;
    originalGlobalEventSource = (globalThis as typeof globalThis & {
      EventSource?: typeof EventSource;
    }).EventSource;

    Object.defineProperty(window, 'EventSource', {
      value: MockEventSource,
      configurable: true,
      writable: true
    });

    Object.defineProperty(globalThis, 'EventSource', {
      value: MockEventSource,
      configurable: true,
      writable: true
    });
  });

  afterAll(() => {
    if (originalWindowEventSource) {
      Object.defineProperty(window, 'EventSource', {
        value: originalWindowEventSource,
        configurable: true,
        writable: true
      });
    } else {
      Reflect.deleteProperty(window as typeof window & { EventSource?: typeof EventSource }, 'EventSource');
    }

    if (originalGlobalEventSource) {
      Object.defineProperty(globalThis, 'EventSource', {
        value: originalGlobalEventSource,
        configurable: true,
        writable: true
      });
    } else {
      Reflect.deleteProperty(globalThis as typeof globalThis & { EventSource?: typeof EventSource }, 'EventSource');
    }
  });

  beforeEach(() => {
    buildEventStreamUrlMock.mockReset();
    MockEventSource.instances = [];
  });

  it('subscribes to the SSE stream and forwards parsed events', () => {
    buildEventStreamUrlMock.mockReturnValue('https://example.invalid/events');
    const received: ProgressEventPayload[] = [];

    const unsubscribe = subscribeToJobEvents('job-42', {
      onEvent: (event) => received.push(event)
    });

    expect(buildEventStreamUrlMock).toHaveBeenCalledWith('job-42');
    expect(MockEventSource.instances).toHaveLength(1);

    const payload: ProgressEventPayload = {
      event_type: 'update',
      timestamp: Date.now(),
      metadata: {},
      snapshot: { completed: 0, total: null, elapsed: 0, speed: 0, eta: null },
      error: null
    };

    MockEventSource.instances[0].emitMessage(JSON.stringify(payload));

    expect(received).toEqual([payload]);

    unsubscribe();
    expect(MockEventSource.instances[0].closed).toBe(true);
  });

  it('invokes the error handler when the stream emits an error', () => {
    buildEventStreamUrlMock.mockReturnValue('https://example.invalid/events');
    const errors: Event[] = [];

    subscribeToJobEvents('job-404', {
      onError: (event) => errors.push(event)
    });

    expect(MockEventSource.instances).toHaveLength(1);

    const errorEvent = new Event('error');
    MockEventSource.instances[0].emitError(errorEvent);

    expect(errors).toContain(errorEvent);
  });

  it('ignores malformed JSON payloads', () => {
    buildEventStreamUrlMock.mockReturnValue('https://example.invalid/events');
    const received: ProgressEventPayload[] = [];

    subscribeToJobEvents('job-500', {
      onEvent: (event) => received.push(event)
    });

    expect(MockEventSource.instances).toHaveLength(1);
    MockEventSource.instances[0].emitMessage('not-json');

    expect(received).toHaveLength(0);
  });
});
