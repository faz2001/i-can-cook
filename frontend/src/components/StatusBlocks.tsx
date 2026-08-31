import { AlertTriangle, RefreshCw } from 'lucide-react';
import React from 'react';

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-on-surface-variant">
      <div className="w-8 h-8 rounded-full border-4 border-primary-container/40 border-t-primary animate-spin" />
      <span className="font-ui text-sm">{label}</span>
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 px-6 text-center">
      <div className="w-14 h-14 rounded-full bg-error-container flex items-center justify-center">
        <AlertTriangle className="text-error" size={26} />
      </div>
      <p className="font-body-md text-on-surface-variant max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-6 py-2.5 rounded-full bg-primary text-on-primary font-ui text-sm font-medium shadow-md hover:shadow-lg transition-shadow"
        >
          <RefreshCw size={16} /> Try again
        </button>
      )}
    </div>
  );
}

export function EmptyBlock({ icon, title, description, action }: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 px-6 text-center">
      {icon}
      <h3 className="font-heading text-lg text-on-surface">{title}</h3>
      {description && <p className="font-body-md text-sm text-on-surface-variant max-w-sm">{description}</p>}
      {action}
    </div>
  );
}

export function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 bg-error-container text-on-error-container rounded-2xl px-4 py-3 text-sm font-ui">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
