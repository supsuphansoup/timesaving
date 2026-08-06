import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  errorMsg: string;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    errorMsg: ''
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMsg: error.message };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 font-['Pretendard',sans-serif]">
          <div className="bg-white p-6 rounded-2xl shadow-xl max-w-lg w-full border border-red-200">
            <h2 className="text-xl font-bold text-red-600 mb-2">화면 렌더링 오류 발생</h2>
            <p className="text-sm text-slate-600 mb-4">현재 화면을 표시하는 도중 예기치 않은 오류가 발생했습니다. 아래 에러 메시지를 확인해주세요.</p>
            <pre className="bg-red-50 text-red-800 p-4 rounded-xl text-xs overflow-auto max-h-64 whitespace-pre-wrap">{this.state.errorMsg}</pre>
            <button 
              onClick={() => {
                this.setState({ hasError: false, errorMsg: '' });
                window.location.reload();
              }}
              className="mt-4 px-4 py-2 bg-slate-900 text-white rounded-lg text-sm hover:bg-slate-800 w-full font-bold"
            >
              페이지 새로고침
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
