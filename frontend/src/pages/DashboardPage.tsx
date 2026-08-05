import React, { useEffect, useState } from 'react';
import {
  Users,
  Building2,
  BookOpen,
  Sparkles,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  History
} from 'lucide-react';
import client from '../api/client';

interface DashboardPageProps {
  onSelectTab: (tab: string) => void;
}

const DashboardPage: React.FC<DashboardPageProps> = ({ onSelectTab }) => {
  const [stats, setStats] = useState({
    professorsCount: 0,
    roomsCount: 0,
    coursesCount: 0,
    candidatesCount: 0,
    confirmedName: '',
  });
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [pRes, rRes, cRes, candRes, logsRes] = await Promise.all([
        client.get('/professors'),
        client.get('/rooms'),
        client.get('/courses'),
        client.get('/timetables/candidates'),
        client.get('/logs'),
      ]);

      const confirmed = candRes.data.find((c: any) => c.status === 'CONFIRMED');

      setStats({
        professorsCount: pRes.data.length,
        roomsCount: rRes.data.length,
        coursesCount: cRes.data.length,
        candidatesCount: candRes.data.length,
        confirmedName: confirmed ? confirmed.name : '미확정',
      });
      setLogs(logsRes.data.slice(0, 5));
    } catch (err) {
      console.error('Failed to load dashboard stats', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center space-x-2 text-blue-400 text-xs font-semibold mb-2">
            <Sparkles className="w-4 h-4" />
            <span>동서대학교 강의실 시간표 최적 배정 시스템</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight">2026학년도 2학기 시간표 배정 대시보드</h2>
          <p className="text-xs text-slate-300 max-w-2xl mt-1">
            교수 6대 제약조건과 컴퓨터실 수용인원 등 하드/소프트 제약조건을 준수하여 최적의 시간표를 자동으로 생성하고 검증합니다.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={() => onSelectTab('generate')}
              className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-blue-500/30 flex items-center space-x-2 transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>시간표 자동 생성 실행</span>
            </button>
            <button
              onClick={() => onSelectTab('compare')}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs px-4 py-2.5 rounded-xl border border-slate-700 flex items-center space-x-2 transition-all"
            >
              <span>추천안 비교 & 수동 수정</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.professorsCount}명</div>
            <div className="text-xs font-semibold text-slate-500">등록된 교수 (6대 제약)</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.roomsCount}개소</div>
            <div className="text-xs font-semibold text-slate-500">관리 강의실</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.coursesCount}개 과목</div>
            <div className="text-xs font-semibold text-slate-500">배정 대상 강의</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.candidatesCount}개안</div>
            <div className="text-xs font-semibold text-slate-500">생성된 추천안 후보</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-900 truncate max-w-[120px]">{stats.confirmedName}</div>
            <div className="text-xs font-semibold text-slate-500">최종 확정 시간표</div>
          </div>
        </div>
      </div>

      {/* Constraints & Recent History Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Hard & Soft Rules Checklist */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-blue-600" />
              <h3 className="font-bold text-slate-900 text-base">알고리즘 제약조건 준수 상태</h3>
            </div>
            <span className="text-xs text-emerald-600 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              자동 배정 엔진 연동 중
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-slate-800">HC-01~02: 중복 배정 방지</div>
                <div className="text-slate-500 text-[11px]">동일 시간대 강의실 및 교수 중복 배정 절대 금지</div>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-slate-800">HC-03~06: 교수 제약 준수</div>
                <div className="text-slate-500 text-[11px]">불가 요일/교시, 고정 강의실 및 불가 강의실 강제</div>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-slate-800">HC-07~08: 컴퓨터실 & 수용인원</div>
                <div className="text-slate-500 text-[11px]">실습 수업 컴퓨터실 지정 및 예상 수강인원 수용성 검증</div>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-slate-800">SC-01~02: 선호도 가중치 극대화</div>
                <div className="text-slate-500 text-[11px]">교수 선호 요일 및 선호 교시 점수화 정렬 지원</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Recent Activity Log */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <History className="w-5 h-5 text-indigo-600" />
              <h3 className="font-bold text-slate-900 text-base">최근 작업 이력</h3>
            </div>
            <button
              onClick={() => onSelectTab('logs')}
              className="text-xs text-blue-600 font-semibold hover:underline"
            >
              전체 보기
            </button>
          </div>

          <div className="space-y-3">
            {logs.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-6">기록된 이력이 없습니다.</p>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="text-xs border-b border-slate-100 pb-2 last:border-0">
                  <div className="flex items-center justify-between text-slate-400 text-[10px]">
                    <span className="font-semibold text-slate-600">{log.username}</span>
                    <span>{new Date(log.timestamp).toLocaleString('ko-KR')}</span>
                  </div>
                  <div className="font-medium text-slate-800 mt-1">{log.message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
