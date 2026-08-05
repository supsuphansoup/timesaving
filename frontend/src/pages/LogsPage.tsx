import React, { useEffect, useState } from 'react';
import { History, ShieldCheck, Sparkles, Edit, CheckCircle, RefreshCw } from 'lucide-react';
import { AuditLogItem } from '../types';
import client from '../api/client';

const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [category, setCategory] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
  }, [category]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await client.get('/logs', {
        params: { category },
      });
      setLogs(res.data);
    } catch (err) {
      console.error('Failed to fetch audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'LOGIN':
        return (
          <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-bold text-[10px] flex items-center space-x-1">
            <ShieldCheck className="w-3 h-3 text-blue-500" />
            <span>로그인 이력</span>
          </span>
        );
      case 'GENERATE':
        return (
          <span className="bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full font-bold text-[10px] flex items-center space-x-1">
            <Sparkles className="w-3 h-3 text-purple-500" />
            <span>시간표 생성</span>
          </span>
        );
      case 'UPDATE':
        return (
          <span className="bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-bold text-[10px] flex items-center space-x-1">
            <Edit className="w-3 h-3 text-amber-500" />
            <span>정보/수정 이력</span>
          </span>
        );
      case 'CONFIRM':
        return (
          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full font-bold text-[10px] flex items-center space-x-1">
            <CheckCircle className="w-3 h-3 text-emerald-500" />
            <span>최종 확정</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-slate-600 font-semibold text-xs mb-1">
            <History className="w-4 h-4 text-blue-600" />
            <span>이력 및 감사 로그 관리</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">로그인, 시간표 생성, 수정 및 확정 이력</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            작업 이력, 시간표 자동 생성 이력, 수동 시간표 수정 및 학기 시간표 최종 확정 이력을 투명하게 저장하고 조회합니다.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs px-3.5 py-2 rounded-xl border border-slate-200 flex items-center space-x-1.5 transition-all shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>새로고침</span>
        </button>
      </div>

      {/* Category Tabs Filter */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap gap-2 text-xs">
        <button
          onClick={() => setCategory('ALL')}
          className={`px-3 py-1.5 rounded-xl font-bold transition-all ${
            category === 'ALL' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          전체 이력
        </button>

        <button
          onClick={() => setCategory('LOGIN')}
          className={`px-3 py-1.5 rounded-xl font-bold transition-all ${
            category === 'LOGIN' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          로그인 이력
        </button>

        <button
          onClick={() => setCategory('GENERATE')}
          className={`px-3 py-1.5 rounded-xl font-bold transition-all ${
            category === 'GENERATE' ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          시간표 생성 이력
        </button>

        <button
          onClick={() => setCategory('UPDATE')}
          className={`px-3 py-1.5 rounded-xl font-bold transition-all ${
            category === 'UPDATE' ? 'bg-amber-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          수정 이력
        </button>

        <button
          onClick={() => setCategory('CONFIRM')}
          className={`px-3 py-1.5 rounded-xl font-bold transition-all ${
            category === 'CONFIRM' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          최종 확정 이력
        </button>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-slate-100/80 border-b border-slate-200 text-slate-600 font-semibold">
                <th className="p-3.5">일시</th>
                <th className="p-3.5">구분</th>
                <th className="p-3.5">작업자</th>
                <th className="p-3.5">상세 작업 내용</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-slate-400">
                    조회된 이력이 없습니다.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-3.5 text-slate-500 font-mono">
                      {new Date(log.timestamp).toLocaleString('ko-KR')}
                    </td>
                    <td className="p-3.5">{getCategoryBadge(log.category)}</td>
                    <td className="p-3.5 font-bold text-slate-800">{log.username}</td>
                    <td className="p-3.5 text-slate-800 font-medium">{log.message}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
