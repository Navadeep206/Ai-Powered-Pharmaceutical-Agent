import React from 'react';
import { AlertTriangle, RotateCcw, Home } from 'lucide-react';
import Button from './Button';

/**
 * Enterprise Application Error Boundary.
 * Catches unhandled React rendering exceptions and displays a helpful GxP fallback UI
 * to prevent the entire browser viewport from crashing to a blank white screen.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('RootIQ ErrorBoundary captured component failure:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[420px] flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-white p-6 sm:p-8 rounded-2xl border border-[#CBD5E1] shadow-lg text-center space-y-5">
            <div className="w-14 h-14 rounded-2xl bg-[#FEF2F2] text-[#DC2626] flex items-center justify-center mx-auto border border-[#FECACA] shadow-inner">
              <AlertTriangle className="w-7 h-7" />
            </div>

            <div className="space-y-1.5">
              <h3 className="text-base font-bold text-[#142B45]">
                {this.props.title || 'An unexpected interface error occurred'}
              </h3>
              <p className="text-xs text-[#64748B] leading-relaxed max-w-sm mx-auto">
                {this.state.error?.message ||
                  'The quality view encountered a rendering error. Your session and backend data remain secure.'}
              </p>
            </div>

            <div className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-left text-[11px] font-mono text-[#64748B] max-h-28 overflow-y-auto">
              <p className="font-semibold text-[#142B45] mb-1">Diagnostic Details:</p>
              <p className="text-[#DC2626] break-words">
                {this.state.error?.toString() || 'Unknown runtime error'}
              </p>
            </div>

            <div className="flex items-center justify-center space-x-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                leftIcon={RotateCcw}
                onClick={this.handleReset}
              >
                Try Again
              </Button>
              <Button
                variant="accent"
                size="sm"
                leftIcon={Home}
                onClick={() => {
                  window.location.href = '/';
                }}
              >
                Return to Dashboard
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

