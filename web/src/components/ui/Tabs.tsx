import {
  ButtonHTMLAttributes,
  HTMLAttributes,
  MouseEventHandler,
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useState,
} from 'react';

type TabsOrientation = 'horizontal' | 'vertical';

type TabsValue = string | null;

interface TabsContextValue {
  value: TabsValue;
  setValue: (value: string) => void;
  registerTab: (value: string) => void;
  unregisterTab: (value: string) => void;
  orientation: TabsOrientation;
  baseId: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

interface TabsProps extends HTMLAttributes<HTMLDivElement> {
  value?: string | null;
  defaultValue?: string | null;
  onValueChange?: (value: string) => void;
  orientation?: TabsOrientation;
  children: ReactNode;
}

export function Tabs({
  value,
  defaultValue = null,
  onValueChange,
  orientation = 'horizontal',
  children,
  ...props
}: TabsProps) {
  const baseId = useId();
  const [internalValue, setInternalValue] = useState<TabsValue>(value ?? defaultValue ?? null);
  const [registeredValues, setRegisteredValues] = useState<string[]>(() => {
    if (defaultValue && typeof defaultValue === 'string') {
      return [defaultValue];
    }
    return [];
  });
  const isControlled = value !== undefined;
  const currentValue = (isControlled ? value : internalValue) ?? null;

  const handleValueChange = useCallback(
    (nextValue: string) => {
      if (!isControlled) {
        setInternalValue(nextValue);
      }
      onValueChange?.(nextValue);
    },
    [isControlled, onValueChange],
  );

  const registerTab = useCallback((tabValue: string) => {
    setRegisteredValues((prev) => {
      if (prev.includes(tabValue)) {
        return prev;
      }
      return [...prev, tabValue];
    });
  }, []);

  const unregisterTab = useCallback((tabValue: string) => {
    setRegisteredValues((prev) => prev.filter((valueItem) => valueItem !== tabValue));
  }, []);

  useEffect(() => {
    if (currentValue) {
      return;
    }

    const fallback = (defaultValue && registeredValues.includes(defaultValue))
      ? defaultValue
      : registeredValues[0];

    if (fallback) {
      handleValueChange(fallback);
    }
  }, [currentValue, defaultValue, handleValueChange, registeredValues]);

  const contextValue = useMemo<TabsContextValue>(
    () => ({
      value: currentValue,
      setValue: handleValueChange,
      registerTab,
      unregisterTab,
      orientation,
      baseId,
    }),
    [baseId, currentValue, handleValueChange, orientation, registerTab, unregisterTab],
  );

  return (
    <TabsContext.Provider value={contextValue}>
      <div data-orientation={orientation} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

function useTabsContext(component: string): TabsContextValue {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error(`${component} must be used within a Tabs component.`);
  }
  return context;
}

interface TabsListProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function TabsList({ children, ...props }: TabsListProps) {
  const { orientation } = useTabsContext('TabsList');
  return (
    <div role="tablist" aria-orientation={orientation} {...props}>
      {children}
    </div>
  );
}

interface TabsTriggerProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  children: ReactNode;
}

export function TabsTrigger({ value, children, onClick, ...props }: TabsTriggerProps) {
  const { value: activeValue, setValue, registerTab, unregisterTab, baseId } = useTabsContext('TabsTrigger');
  const triggerId = `${baseId}-trigger-${value}`;
  const panelId = `${baseId}-content-${value}`;
  const isActive = activeValue === value;

  useEffect(() => {
    registerTab(value);
    return () => {
      unregisterTab(value);
    };
  }, [registerTab, unregisterTab, value]);

  const handleClick: MouseEventHandler<HTMLButtonElement> = (event) => {
    onClick?.(event);
    if (event.defaultPrevented) {
      return;
    }
    setValue(value);
  };

  return (
    <button
      {...props}
      type="button"
      role="tab"
      id={triggerId}
      aria-selected={isActive}
      aria-controls={panelId}
      data-state={isActive ? 'active' : 'inactive'}
      onClick={handleClick}
    >
      {children}
    </button>
  );
}

interface TabsContentProps extends HTMLAttributes<HTMLDivElement> {
  value: string;
  children: ReactNode;
}

export function TabsContent({ value, children, ...props }: TabsContentProps) {
  const { value: activeValue, baseId } = useTabsContext('TabsContent');
  const triggerId = `${baseId}-trigger-${value}`;
  const panelId = `${baseId}-content-${value}`;
  const hidden = activeValue !== value;

  return (
    <div
      {...props}
      role="tabpanel"
      id={panelId}
      aria-labelledby={triggerId}
      hidden={hidden}
      data-state={hidden ? 'inactive' : 'active'}
    >
      {children}
    </div>
  );
}

