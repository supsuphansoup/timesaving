import React, { useEffect, useState } from 'react';
import { GitCompare, CheckCircle2, Lock, Sparkles, AlertCircle, RefreshCw, Layers , Cpu} from 'lucide-react';
import { Candidate, Room, Course, Professor } from '../types';
import TimetableGrid from '../components/TimetableGrid';
import client from '../api/client';

const ComparePage: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const [reassigning, setReassigning] = useState(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [candRes, rRes, cRes, pRes] = await Promise.all([
        client.get('/timetables/candidates'),
        client.get('/rooms'),
        client.get('/courses'),
        client.get('/professors'),
      ]);
      setCandidates(candRes.data);
      setRooms(rRes.data);
      setCourses(cRes.data);
      setProfessors(pRes.data);

      if (candRes.data.length > 0 && !selectedCandidateId) {
        setSelectedCandidateId(candRes.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch compare data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshCandidate = async () => {
    try {
      const candRes = await client.get('/timetables/candidates');
      setCandidates(candRes.data);
      if (selectedCandidateId) {
        const detailRes = await client.get(`/timetables/${selectedCandidateId}`);
        setActiveTimetable(detailRes.data);
      }
    } catch (err) {
      console.error('Failed to refresh candidates', err);
    }
  };

  
  const [activeTimetable, setActiveTimetable] = useState<any>(null);

  useEffect(() => {
    if (selectedCandidateId) {
      client.get(`/timetables/${selectedCandidateId}`)
        .then(res => setActiveTimetable(res.data))
        .catch(err => console.error('Failed to fetch timetable details', err));
    } else {
      setActiveTimetable(null);
    }
  }, [selectedCandidateId]);

const activeCandidate = candidates.find((c) => c.id === selectedCandidateId);
  
  const sortedCandidates = [...candidates]
    .sort((a, b) => (b.constraint_satisfaction_rate || 0) - (a.constraint_satisfaction_rate || 0))
    .slice(0, 5);


  const handleGenerate = async () => {
    setGenerating(true);
    setGenerateError(null);

    try {
      const res = await client.post('/timetables/generate', {
        semester_id: 1,
        num_candidates: 5,
      });
      const taskId = res.data.task_id;
      
      const interval = setInterval(async () => {
        try {
          const statusRes = await client.get(`/timetables/tasks/${taskId}`);
          const status = statusRes.data.status;
          if (status === 'COMPLETED') {
            clearInterval(interval);
            const candRes = await client.get('/timetables/candidates');
            setCandidates(candRes.data);
            if (candRes.data.length > 0) {
              setSelectedCandidateId(candRes.data[0].id);
            }
            setGenerating(false);
          } else if (status === 'INFEASIBLE' || status === 'FAILED') {
            clearInterval(interval);
            setGenerateError(statusRes.data.message || '생성 실패');
            setGenerating(false);
          }
        } catch (err) {
          console.error(err);
        }
      }, 2000);
      
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'object' && detail !== null ? detail.message : detail;
      setGenerateError(errorMsg || '시간표 자동 생성 중 오류가 발생했습니다.');
      setGenerating(false);
    }
  };

// Partial Re-assignment
  const handlePartialReassign = async () => {
    if (!activeCandidate) return;

    const lockedIds = (activeTimetable?.assignments || [])
      .filter((a: any) => a.is_locked)
      .map((a: any) => a.id);

    if (lockedIds.length === 0) {
      if (!confirm('고정(Lock)된 수업이 없습니다. 전체 수업을 다시 재배정하시겠습니까?')) {
        return;
      }
    }

    setReassigning(true);
    try {
      const res = await client.post('/timetables/reassign', {
        timetable_id: activeCandidate.id,
        fixed_assignment_ids: lockedIds,
      });
      const taskId = res.data.task_id;
      
      // Poll
      const interval = setInterval(async () => {
        try {
          const statusRes = await client.get(`/timetables/tasks/${taskId}`);
          const status = statusRes.data.status;
          if (status === 'COMPLETED') {
            clearInterval(interval);
            const candRes = await client.get('/timetables/candidates');
            setCandidates(candRes.data);
            if (candRes.data.length > 0) {
              setSelectedCandidateId(candRes.data[0].id);
            }
            alert(`부분 재배정 완료! (고정 수업 ${lockedIds.length}개 유지됨)`);
            setReassigning(false);
          } else if (status === 'INFEASIBLE' || status === 'FAILED') {
            clearInterval(interval);
            alert(statusRes.data.message || '부분 재배정 실패');
            setReassigning(false);
          }
        } catch (err) {
          console.error(err);
        }
      }, 2000);

    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'object' && detail !== null ? detail.message : detail;
      alert(errorMsg || '부분 재배정 요청 실패');
      setReassigning(false);
    }
  };

  const handleConfirmTimetable = async (candidateId: number) => {
    if (!confirm('이 추천안을 2026학년도 2학기 최종 확정 시간표로 지정하시겠습니까?')) return;
    try {
      await client.post(`/timetables/confirm/${candidateId}`);
      handleRefreshCandidate();
      alert('최종 확정 시간표로 지정되었습니다!');
    } catch (err: any) {
      alert(err.response?.data?.detail || '확정 실패');
    }
  };

  return (
    <div className="space-y-6">

      {/* Top Banner - Generate */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-purple-600 font-semibold text-xs mb-1">
            <Sparkles className="w-4 h-4" />
            <span>최적 탐색 알고리즘 기반 시간표 자동 생성</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">시간표 추천안 생성 & 통합 비교</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            제약조건을 만족하는 추천안 후보들을 자동 생성하고, 바로 아래에서 비교 및 수동 수정할 수 있습니다.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          

          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-purple-500/20 flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            <Cpu className="w-4 h-4" />
            <span>{generating ? '시간표 연산 중...' : '시간표 자동 생성 실행'}</span>
          </button>
        </div>
      </div>

      {/* Error Box */}
      {generateError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-2xl p-4 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-red-900">시간표 생성 불가 (하드 제약 충돌)</div>
            <div className="mt-1 leading-relaxed">{generateError}</div>
          </div>
        </div>
      )}

      {/* Loading state animation */}
      {generating && (
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

      {/* Header Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-blue-600 font-semibold text-xs mb-1">
            <GitCompare className="w-4 h-4" />
            <span>추천안 비교 및 반자동 수정</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">시간표 추천안 비교, 수동 수정 & 부분 재배정</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            생성된 추천안 후보의 지표를 비교하고, 시간표 셀을 클릭하여 수동 수정(실시간 충돌검증)하거나 특정 강의를 고정한 후 부분 재배정합니다.
          </p>
        </div>

        {activeCandidate && (
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handlePartialReassign}
              disabled={reassigning}
              className="bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-amber-500/20 flex items-center space-x-1.5 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${reassigning ? 'animate-spin' : ''}`} />
              <span>고정 강의 유지 & 부분 재배정</span>
            </button>

            <button
              onClick={() => handleConfirmTimetable(activeCandidate.id)}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-emerald-500/20 flex items-center space-x-1.5 transition-all"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>최종 시간표 확정</span>
            </button>
          </div>
        )}
      </div>

      {candidates.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 space-y-2">
          <AlertCircle className="w-8 h-8 text-slate-300 mx-auto" />
          <div className="font-bold text-slate-700">생성된 추천안이 없습니다.</div>
          <p className="text-xs text-slate-500">'시간표 자동 생성' 메뉴에서 추천안을 먼저 생성해주세요.</p>
        </div>
      ) : (
        <div className="space-y-6">

      {/* Comparison Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <span>추천안 종합 비교 테이블</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="p-3">선택</th>
                    <th className="p-3">적합도</th>
                    <th className="p-3">상태</th>
                    <th className="p-3">선호도 반영률 (Soft Rate)</th>
                    <th className="p-3">만족한 Soft Constraint</th>
                    <th className="p-3">하드 제약 위반</th>
                    <th className="p-3 text-right">작업</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sortedCandidates.map((cand: Candidate) => {
                    const isSelected = cand.id === selectedCandidateId;
                    const isConfirmed = cand.status === 'CONFIRMED';
                    return (
                      <tr
                        key={cand.id}
                        onClick={() => setSelectedCandidateId(cand.id)}
                        className={`cursor-pointer transition-colors ${isSelected ? 'bg-blue-50/70 font-medium' : 'hover:bg-slate-50'
                          }`}
                      >
                        <td className="p-3">
                          <input
                            type="radio"
                            name="cand_select"
                            checked={isSelected}
                            onChange={() => setSelectedCandidateId(cand.id)}
                            className="w-4 h-4 text-blue-600"
                          />
                        </td>
                        <td className="p-3 font-bold text-slate-800">
                          {cand.name} ({Math.round(cand.constraint_satisfaction_rate * 100)}%)
                        </td>
                        <td className="p-3">
                          {isConfirmed ? (
                            <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-300">
                              최종 확정
                            </span>
                          ) : (
                            <span className="bg-slate-100 text-slate-600 text-[10px] font-semibold px-2 py-0.5 rounded-full">
                              후보
                            </span>
                          )}
                        </td>
                        <td className="p-3 font-extrabold text-blue-600">{cand.constraint_satisfaction_rate?.toFixed(1) || 0}%</td>
                        <td className="p-3 text-emerald-600 font-semibold">0건 (정상)</td>
                        <td className="p-3 text-right space-x-1">
                          {!isConfirmed && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleConfirmTimetable(cand.id);
                              }}
                              className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg font-semibold text-[11px]"
                            >
                              확정하기
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Detailed Interactive Timetable Grid */}
          {activeCandidate && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-slate-900 text-base">{activeCandidate.name} 상세 시간표</h3>
                  <span className="text-xs text-slate-500 font-normal">
                    (수업을 클릭하면 시간/강의실 수용성 검증 후 수동 변경 가능, 자물쇠 클릭 시 고정)
                  </span>
                </div>

                <div className="flex items-center space-x-3 text-xs text-slate-600">
                  <span className="flex items-center space-x-1">
                    <Lock className="w-3.5 h-3.5 text-amber-500" />
                    <span>고정된 강의: {(activeTimetable?.assignments || []).filter((a: any) => a.is_locked).length}개</span>
                  </span>
                </div>
              </div>

              <TimetableGrid
                assignments={(activeTimetable?.assignments || [])}
                candidateId={activeCandidate.id}
                rooms={rooms}
                courses={courses}
                professors={professors}
                onAssignmentUpdated={handleRefreshCandidate}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ComparePage;
