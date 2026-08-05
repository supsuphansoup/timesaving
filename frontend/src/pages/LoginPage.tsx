import React, { useState } from 'react';
import { Lock, User, GraduationCap, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import client from '../api/client';

interface LoginPageProps {
  onLoginSuccess: (user: any, token: string) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('password123!');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await client.post('/auth/login', { username, password });
      const { access_token, name, role } = res.data;
      const userData = { username, name, role };
      
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));

      onLoginSuccess(userData, access_token);
    } catch (err: any) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다. 아이디 및 비밀번호를 확인해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Background Decorative Blur circles */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none"></div>

      <div className="max-w-md w-full relative z-10">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 text-white shadow-xl shadow-blue-500/30 mb-4">
            <GraduationCap className="w-10 h-10" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">동서대학교 강의실 시간표 배정 시스템</h1>
          <p className="text-xs text-slate-400 mt-1">Dongseo University Timetable Optimization System</p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-4 mb-6">
            <ShieldCheck className="w-5 h-5 text-blue-500" />
            <h2 className="text-slate-200 font-semibold text-base">조교 인증 로그인</h2>
          </div>

          {error && (
            <div className="mb-5 bg-red-500/10 border border-red-500/30 text-red-400 text-xs rounded-2xl p-3.5 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5">조교 아이디</label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full bg-slate-800/80 text-slate-100 pl-10 pr-4 py-2.5 text-xs rounded-xl border border-slate-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-600"
                  placeholder="아이디 입력"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5">비밀번호</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-slate-800/80 text-slate-100 pl-10 pr-4 py-2.5 text-xs rounded-xl border border-slate-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-600"
                  placeholder="비밀번호 입력"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs py-3 rounded-xl shadow-lg shadow-blue-600/30 flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
            >
              <span>{loading ? '인증 진행 중...' : '로그인'}</span>
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>

          {/* Preset Demo Box */}
          <div className="mt-6 pt-4 border-t border-slate-800/80 text-center">
            <p className="text-[11px] text-slate-500">데모 로그인 계정: <span className="text-slate-300 font-mono">admin</span> / 비밀번호: <span className="text-slate-300 font-mono">password123!</span></p>
          </div>
        </div>

        {/* System Footer */}
        <p className="text-center text-[11px] text-slate-600 mt-6">
          © 2026 Dongseo University Timetable System. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
