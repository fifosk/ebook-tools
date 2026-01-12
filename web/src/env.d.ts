/// <reference types="vite/client" />

interface Window {
  AppleID?: {
    auth: {
      init: (config: Record<string, unknown>) => void;
      signIn: () => Promise<any>;
    };
  };
  google?: {
    accounts?: {
      id?: {
        initialize: (config: Record<string, unknown>) => void;
        renderButton: (container: HTMLElement, options?: Record<string, unknown>) => void;
      };
    };
  };
}
