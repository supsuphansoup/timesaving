import React, { useEffect, useState } from 'react';
import { GitCompare, CheckCircle2, Lock, Sparkles, AlertCircle, RefreshCw, Layers } from 'lucide-react';
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
    } catch (err) {
      console.error('Failed to refresh candidates', err);
    }
  };

  const activeCandidate = candidates.find((c) => c.id === selectedCandidateId);

  // Partial Re-assignment
  const handlePartialReassign = async () => {
    if (!activeCandidate) return;

    // Collect locked assignment IDs
    const lockedIds = activeCandidate.assignments
      .filter((a) => a.is_locked)
      .map((a) => a.id);

    if (lockedIds.length === 0) {
      if (!confirm('고정(Lock)된 수업이 없습니다. 전체 수업을 다시 재배정하시겠습니까?')) {
        return;
      }
    }

    setReassigning(true);
    try {
      const res = await client.post('/timetables/generate', {
        semester_id: 1,
        num_candidates: 3,
        locked_assignment_ids: lockedIds,
      });

      setCandidates(res.data);
      if (res.data.length > 0) {
        setSelectedCandidateId(res.data[0].id);
      }
      alert(`부분 재배정 완료! (고정 수업 ${lockedIds.length}개 유지됨)`);
    } catch (err: any) {
      alert(err.response?.data?.detail || '부분 재배정 실패');
    } finally {
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
                    <th className="p-3">추천안 명칭</th>
                    <th className="p-3">상태</th>
                    <th className="p-3">선호도 반영률 (Soft Rate)</th>
                    <th className="p-3">만족한 Soft Constraint</th>
                    <th className="p-3">하드 제약 위반</th>
                    <th className="p-3 text-right">작업</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {candidates.map((cand) => {
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
                          {cand.name}
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
                        <td className="p-3 font-extrabold text-blue-600">{cand.satisfaction_rate}%</td>
                        <td className="p-3 text-slate-700">{cand.satisfied_soft_constraints}개 만족</td>
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
                    <span>고정된 강의: {activeCandidate.assignments.filter((a) => a.is_locked).length}개</span>
                  </span>
                </div>
              </div>

              <TimetableGrid
                assignments={activeCandidate.assignments}
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
