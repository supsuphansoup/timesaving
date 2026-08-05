import React, { useState } from 'react';
import { Assignment, Room, Course, Professor } from '../types';
import { Lock, Unlock, Monitor, Edit3, Building, User, BookOpen } from 'lucide-react';
import client from '../api/client';

interface TimetableGridProps {
  assignments: Assignment[];
  candidateId?: number;
  rooms?: Room[];
  courses?: Course[];
  professors?: Professor[];
  onAssignmentUpdated?: () => void;
  readOnly?: boolean;
}

const DAYS = ['월', '화', '수', '목', '금'];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

const PERIOD_TIMES = [
  '09:00 - 09:50',
  '10:00 - 10:50',
  '11:00 - 11:50',
  '12:00 - 12:50',
  '13:00 - 13:50',
  '14:00 - 14:50',
  '15:00 - 15:50',
  '16:00 - 16:50',
  '17:00 - 17:50',
];

const COLOR_PALETTE = [
  'bg-blue-50 border-blue-200 text-blue-900 hover:bg-blue-100',
  'bg-indigo-50 border-indigo-200 text-indigo-900 hover:bg-indigo-100',
  'bg-emerald-50 border-emerald-200 text-emerald-900 hover:bg-emerald-100',
  'bg-amber-50 border-amber-200 text-amber-900 hover:bg-amber-100',
  'bg-purple-50 border-purple-200 text-purple-900 hover:bg-purple-100',
  'bg-rose-50 border-rose-200 text-rose-900 hover:bg-rose-100',
  'bg-teal-50 border-teal-200 text-teal-900 hover:bg-teal-100',
  'bg-cyan-50 border-cyan-200 text-cyan-900 hover:bg-cyan-100',
];

const TimetableGrid: React.FC<TimetableGridProps> = ({
  assignments,
  candidateId,
  rooms = [],
  onAssignmentUpdated,
  readOnly = false,
}) => {
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null);
  const [editDay, setEditDay] = useState('월');
  const [editPeriod, setEditPeriod] = useState(1);
  const [editRoomId, setEditRoomId] = useState<number>(0);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [updating, setUpdating] = useState(false);

  // Assign distinct background color per course ID
  const getCourseColor = (courseId: number) => {
    return COLOR_PALETTE[courseId % COLOR_PALETTE.length];
  };

  const handleOpenEditModal = (a: Assignment) => {
    if (readOnly) return;
    setSelectedAssignment(a);
    setEditDay(a.day);
    setEditPeriod(a.start_period);
    setEditRoomId(a.room_id);
    setValidationError(null);
  };

  const handleToggleLock = async (e: React.MouseEvent, assignmentId: number) => {
    e.stopPropagation();
    if (readOnly) return;
    try {
      await client.post(`/timetables/toggle-lock/${assignmentId}`);
      if (onAssignmentUpdated) onAssignmentUpdated();
    } catch (err: any) {
      alert(err.response?.data?.detail || '고정 상태 변경 실패');
    }
  };

  const handleManualEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssignment || !candidateId) return;

    setUpdating(true);
    setValidationError(null);

    try {
      await client.post('/timetables/manual-edit', {
        candidate_id: candidateId,
        assignment_id: selectedAssignment.id,
        new_day: editDay,
        new_start_period: editPeriod,
        new_room_id: editRoomId,
      });

      setSelectedAssignment(null);
      if (onAssignmentUpdated) onAssignmentUpdated();
    } catch (err: any) {
      setValidationError(err.response?.data?.detail || '수동 변경에 실패했습니다.');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="w-full overflow-x-auto bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
      <table className="w-full border-collapse text-xs min-w-[700px]">
        <thead>
          <tr className="bg-slate-100/80 border-b border-slate-200">
            <th className="p-2 border-r border-slate-200 w-24 text-slate-500 font-semibold text-center">교시 / 시간</th>
            {DAYS.map((day) => (
              <th key={day} className="p-2 font-bold text-slate-700 text-center w-1/5">
                {day}요일
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PERIODS.map((period) => (
            <tr key={period} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
              <td className="p-2 border-r border-slate-200 text-center bg-slate-50">
                <div className="font-bold text-slate-700">{period}교시</div>
                <div className="text-[10px] text-slate-400">{PERIOD_TIMES[period - 1]}</div>
              </td>
              {DAYS.map((day) => {
                // Find assignment that occupies (day, period)
                const assign = assignments.find((a) => {
                  if (a.day !== day) return false;
                  return period >= a.start_period && period < a.start_period + a.duration;
                });

                // Only render cell content at the start period of the block
                const isStart = assign && assign.start_period === period;

                if (assign && !isStart) {
                  return null; // Merged block
                }

                return (
                  <td
                    key={`${day}-${period}`}
                    rowSpan={isStart ? assign.duration : 1}
                    className="p-1 border-r border-slate-200 align-top relative h-16"
                  >
                    {assign && isStart && (
                      <div
                        onClick={() => handleOpenEditModal(assign)}
                        className={`h-full w-full rounded-xl border p-2 flex flex-col justify-between cursor-pointer transition-all shadow-sm hover:shadow-md ${getCourseColor(
                          assign.course_id
                        )}`}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-1">
                            <span className="font-bold text-xs leading-tight">{assign.course_name}</span>
                            <div className="flex items-center space-x-1 shrink-0">
                              {assign.is_computer_lab && (
                                <span className="bg-cyan-600 text-white p-0.5 rounded text-[9px]" title="실습실">
                                  <Monitor className="w-3 h-3" />
                                </span>
                              )}
                              {!readOnly && (
                                <button
                                  onClick={(e) => handleToggleLock(e, assign.id)}
                                  className={`p-0.5 rounded transition-colors ${
                                    assign.is_locked ? 'bg-amber-500 text-white' : 'text-slate-400 hover:text-slate-600'
                                  }`}
                                  title={assign.is_locked ? '고정됨 (재배정 시 유지)' : '고정 안 됨'}
                                >
                                  {assign.is_locked ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                                </button>
                              )}
                            </div>
                          </div>
                          <div className="text-[11px] font-medium opacity-80 mt-0.5 flex items-center space-x-1">
                            <User className="w-3 h-3" />
                            <span>{assign.professor_name} 교수</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-[10px] opacity-75 border-t border-slate-200/50 pt-1 mt-1">
                          <span className="flex items-center space-x-0.5">
                            <Building className="w-3 h-3" />
                            <span className="font-semibold">{assign.room_name}</span>
                          </span>
                          <span>
                            {assign.department} {assign.grade}학년({assign.section})
                          </span>
                        </div>
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Manual Edit Modal */}
      {selectedAssignment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center space-x-2">
                <Edit3 className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-base">수업 시간/강의실 수동 변경</h3>
              </div>
              <button
                onClick={() => setSelectedAssignment(null)}
                className="text-slate-400 hover:text-slate-600 font-bold px-2"
              >
                ✕
              </button>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 mb-4 text-xs space-y-1">
              <div className="font-bold text-blue-900">{selectedAssignment.course_name}</div>
              <div className="text-blue-700">
                담당: {selectedAssignment.professor_name} 교수 | {selectedAssignment.department} {selectedAssignment.grade}학년 ({selectedAssignment.duration}시간 연속강의)
              </div>
            </div>

            {validationError && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl p-3 whitespace-pre-line">
                {validationError}
              </div>
            )}

            <form onSubmit={handleManualEditSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">변경 요일</label>
                  <select
                    value={editDay}
                    onChange={(e) => setEditDay(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {DAYS.map((d) => (
                      <option key={d} value={d}>
                        {d}요일
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">시작 교시</label>
                  <select
                    value={editPeriod}
                    onChange={(e) => setEditPeriod(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {PERIODS.map((p) => (
                      <option key={p} value={p}>
                        {p}교시 ({PERIOD_TIMES[p - 1]})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">변경 강의실</label>
                <select
                  value={editRoomId}
                  onChange={(e) => setEditRoomId(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {rooms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.building} {r.name} (수용: {r.capacity}명 {r.is_computer_lab ? '/ 컴퓨터실' : ''})
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-3 flex justify-end space-x-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedAssignment(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-md disabled:opacity-50"
                >
                  {updating ? '검증 및 저장 중...' : '시간표 검증 후 변경'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimetableGrid;
