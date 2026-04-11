import { useState, useRef, useCallback, type ReactNode } from "react";
import {
  useFloating,
  offset,
  flip,
  shift,
  autoUpdate,
  type Placement,
} from "@floating-ui/react-dom";

interface TooltipProps {
  content: ReactNode;
  placement?: Placement;
  children: ReactNode;
}

export default function Tooltip({ content, placement = "top", children }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const { refs, floatingStyles } = useFloating({
    open,
    placement,
    middleware: [offset(8), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  const handleEnter = useCallback(() => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setOpen(true), 200);
  }, []);

  const handleLeave = useCallback(() => {
    clearTimeout(timeoutRef.current);
    setOpen(false);
  }, []);

  return (
    <>
      <span
        ref={refs.setReference}
        onMouseEnter={handleEnter}
        onMouseLeave={handleLeave}
        onFocus={handleEnter}
        onBlur={handleLeave}
        className="inline"
      >
        {children}
      </span>
      {open && (
        <div
          ref={refs.setFloating}
          style={floatingStyles}
          role="tooltip"
          className="z-50 rounded-lg bg-text-primary px-3 py-2 text-sm text-bg shadow-lg max-w-xs"
        >
          {content}
        </div>
      )}
    </>
  );
}
