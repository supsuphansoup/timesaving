import React, { useState } from 'react';
import { Sparkles, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck, Cpu } from 'lucide-react';
import { Candidate } from '../types';
import client from '../api/client';

interface GeneratePageProps {
  onSelectTab: (tab: string) => void;
}

const GeneratePage: React.FC<GeneratePageProps> = ({ onSelectTab }) => {
  const [numCandidates, setNumCandidates] = useState<number>(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedCandidates, setGeneratedCandidates] = useState<Candidate[]>([]);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setGeneratedCandidates([]);

    try {
      const res = await client.post('/timetables/generate', {
        semester_id: 1,
        num_candidates: numCandidates,
      });
      setGeneratedCandidates(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '시간표 자동 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-purple-600 font-semibold text-xs mb-1">
            <Sparkles className="w-4 h-4" />
            <span>최적 탐색 알고리즘 기반 시간표 자동 생성</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">시간표 추천안 생성</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            등록된 교수 6대 제약조건과 컴퓨터실, 강의실 수용 인원 하드 제약조건을 만족하는 추천안 후보들을 다각도로 자동 생성합니다.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <div className="flex items-center space-x-2 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 text-xs">
            <span className="font-semibold text-slate-700">생성 후보 수:</span>
            <select
              value={numCandidates}
              onChange={(e) => setNumCandidates(Number(e.target.value))}
              className="bg-white border rounded-lg px-2 py-1 font-bold text-blue-600 outline-none"
            >
              <option value={3}>3개 추천안 (기본)</option>
              <option value={4}>4개 추천안</option>
              <option value={5}>5개 추천안</option>
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-purple-500/20 flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <Cpu className="w-4 h-4" />
            <span>{loading ? '시간표 연산 중...' : '시간표 자동 생성 실행'}</span>
          </button>
        </div>
      </div>

      {/* Error Box */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-2xl p-4 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-red-900">시간표 생성 불가 (하드 제약 충돌)</div>
            <div className="mt-1 leading-relaxed">{error}</div>
          </div>
        </div>
      )}

      {/* Loading state animation */}
      {loading && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-4 shadow-sm animate-pulse">
          <div className="inline-flex p-4 bg-purple-50 text-purple-600 rounded-full">
            <Sparkles className="w-8 h-8 animate-spin" />
          </div>
          <h3 className="font-bold text-slate-800 text-lg">최적화 로직 가동 중</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            1. 불가 요일/교시 및 강의실 픽스 필터링 <br />
            2. 컴퓨터실 필요 수업 및 수용 인원 매칭 <br />
            3. 선호 요일/교시 점수 극대화 알고리즘 실행...
          </p>
        </div>
      )}

      {/* Generated Results Summary Cards */}
      {generatedCandidates.length > 0 && !loading && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span>생성 완료된 시간표 추천안 ({generatedCandidates.length}개)</span>
            </h3>
            <button
              onClick={() => onSelectTab('compare')}
              className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-4 py-2 rounded-xl shadow shadow-blue-500/20 flex items-center space-x-1.5 transition-all"
            >
              <span>추천안 비교 & 상세 보기</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {generatedCandidates.map((cand, idx) => (
              <div key={cand.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-purple-300 transition-all">
                <div className="border-b border-slate-100 pb-3">
                  <span className="text-[10px] font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                    후보 #{idx + 1}
                  </span>
                  <h4 className="font-bold text-slate-900 text-base mt-1">{cand.name}</h4>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-semibold">선호도 반영률 (Soft Rate):</span>
                    <span className="font-extrabold text-blue-600 text-sm">{cand.satisfaction_rate}%</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-semibold">만족한 Soft Constraint 수:</span>
                    <span className="font-bold text-slate-800">{cand.satisfied_soft_constraints}개</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-semibold">하드 제약 충돌 수:</span>
                    <span className="font-bold text-emerald-600">0건 (완전 준수)</span>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <span className="text-slate-500">배정 수업 수:</span>
                    <span className="font-semibold text-slate-700">{cand.assignments.length}개 강의</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GeneratePage;
