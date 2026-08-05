import React from 'react';
import {
  LayoutDashboard,
  UserCheck,
  Building2,
  BookOpen,
  Sparkles,
  GitCompare,
  CalendarDays,
  History
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

const navItems = [
  { id: 'dashboard', label: '대시보드', icon: LayoutDashboard },
  { id: 'professors', label: '교수 제약조건 관리', icon: UserCheck },
  { id: 'rooms', label: '강의실 정보 관리', icon: Building2 },
  { id: 'courses', label: '강의 정보 관리', icon: BookOpen },
  { id: 'generate', label: '시간표 자동 생성', icon: Sparkles },
  { id: 'compare', label: '추천안 비교 & 수정', icon: GitCompare },
  { id: 'view', label: '시간표 조회 & 출력', icon: CalendarDays },
  { id: 'logs', label: '이력 및 로그 관리', icon: History },
];

const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  return (
    <aside className="no-print w-64 bg-slate-900 border-r border-slate-800 shrink-0 min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between">
      <div className="space-y-6">
        <div>
          <p className="px-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">메인 메뉴</p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer Info Box */}
      <div className="bg-slate-800/60 rounded-xl p-3 border border-slate-700/50 text-slate-400 text-[11px] space-y-1">
        <div className="flex items-center justify-between text-slate-300 font-semibold">
          <span>엔진 정보</span>
          <span className="text-blue-400 font-mono">최적 배정 v1.0</span>
        </div>
        <p className="text-[10px] text-slate-500">강의실 시간표 자동 배정 시스템</p>
      </div>
    </aside>
  );
};

export default Sidebar;
