import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

/**
 * Route-level error boundary. Wraps every top-level page so a single component
 * crash surfaces a friendly card instead of a red screen or blank page.
 * Sentry-free; logs to console for developer debugging.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }
  componentDidUpdate(prevProps) {
    // Reset when the route/user changes.
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false, error: null });
    }
  }
  render() {
    if (!this.state.hasError) return this.props.children;
    const msg = String(this.state.error?.message || this.state.error || "Unknown error");
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-8" data-testid="error-boundary">
        <div className="max-w-lg w-full surface rounded-lg p-6 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-500/15 text-amber-400 mb-3">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="font-display font-bold text-xl mb-1">This page hit a snag</h2>
          <p className="text-xs text-[#A1A1AA] mb-4">
            Something didn't load correctly. Reloading usually fixes it. If it keeps happening,
            let us know which button you tapped just before this appeared.
          </p>
          <pre className="text-[10px] font-mono text-[#71717A] bg-[#0A0A0A] border border-[#27272A] rounded p-3 overflow-x-auto text-left whitespace-pre-wrap" data-testid="error-boundary-msg">
            {msg}
          </pre>
          <div className="flex items-center justify-center gap-2 mt-4">
            <button
              onClick={() => window.location.reload()}
              data-testid="error-boundary-reload"
              className="btn-primary rounded-md gap-2 inline-flex items-center px-4 h-9 text-sm"
            >
              <RefreshCw className="w-4 h-4" /> Reload page
            </button>
            <button
              onClick={() => (window.location.href = "/dashboard")}
              data-testid="error-boundary-home"
              className="btn-ghost rounded-md gap-2 inline-flex items-center px-4 h-9 text-sm border border-[#27272A] hover:border-[#CCFF00]"
            >
              Go to dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }
}
