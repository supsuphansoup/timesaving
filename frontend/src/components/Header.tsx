import React from 'react';
import { ShieldCheck, GraduationCap, LogOut } from 'lucide-react';

interface HeaderProps {
  user?: any;
  onLogout?: () => void;
}

const Header: React.FC<HeaderProps> = ({ user, onLogout }) => {
  return (
    <header className="no-print bg-slate-900 text-white border-b border-slate-800 shadow-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* System Title */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/30">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-white">동서대학교</span>
              <span className="bg-blue-600 text-blue-100 text-xs px-2 py-0.5 rounded-full font-medium">조교 업무용</span>
            </div>
            <p className="text-xs text-slate-400 font-normal">강의실 시간표 자동 배정 & 제약조건 최적화 시스템</p>
          </div>
        </div>

        {/* Right Info & Actions */}
        <div className="flex items-center space-x-4">
          {/* User Info & Actions */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-medium text-slate-200">
                {user?.name ? `${user.name} (${user.department || '부서미상'})` : (user?.username || '사용자')}
              </span>
            </div>
            
            {onLogout && (
              <button 
                onClick={onLogout}
                className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg transition-colors text-sm border border-slate-700"
              >
                <LogOut className="w-4 h-4" />
                <span>로그아웃</span>
              </button>
            )}
          </div>

        </div>
      </div>
    </header>
  );
};

export default Header;
