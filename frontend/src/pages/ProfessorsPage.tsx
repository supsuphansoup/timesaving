import React, { useEffect, useState } from 'react';
import {
  UserCheck,
  Plus,
  Edit2,
  Trash2,
  Check,
  AlertCircle,
  Building,
  Clock,
  Calendar,
  Ban,
  Star,
  RotateCcw,
  Info,
  Sparkles,
  ShieldCheck
} from 'lucide-react';
import { Professor, Room } from '../types';
import client from '../api/client';

const DAYS = ['월', '화', '수', '목', '금'];
const PERIODS = [
  { id: 1, name: '1교시', time: '09:00~10:00' },
  { id: 2, name: '2교시', time: '10:00~11:00' },
  { id: 3, name: '3교시', time: '11:00~12:00' },
  { id: 4, name: '4교시', time: '12:00~13:00' },
  { id: 5, name: '5교시', time: '13:00~14:00' },
  { id: 6, name: '6교시', time: '14:00~15:00' },
  { id: 7, name: '7교시', time: '15:00~16:00' },
  { id: 8, name: '8교시', time: '16:00~17:00' },
  { id: 9, name: '9교시', time: '17:00~18:00' },
];

const ProfessorsPage: React.FC = () => {
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);

  // Form Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProf, setEditingProf] = useState<Professor | null>(null);

  // Form Fields
  const [name, setName] = useState('');
  const [department, setDepartment] = useState('컴퓨터공학과');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [unavailableDays, setUnavailableDays] = useState<string[]>([]);
  const [preferredDays, setPreferredDays] = useState<string[]>([]);
  const [unavailablePeriods, setUnavailablePeriods] = useState<number[]>([]);
  const [preferredPeriods, setPreferredPeriods] = useState<number[]>([]);
  const [unavailableSlots, setUnavailableSlots] = useState<string[]>([]); // e.g. ["월-1", "화-3"]
  const [preferredSlots, setPreferredSlots] = useState<string[]>([]);     // e.g. ["수-5", "목-6"]
  const [fixedRoomId, setFixedRoomId] = useState<number | null>(null);
  const [unavailableRoomIds, setUnavailableRoomIds] = useState<number[]>([]);
  const [weeklyHoursLimit, setWeeklyHoursLimit] = useState(15);

  // Timetable Grid Editor Active Mode: 'unavailable' (Hard) | 'preferred' (Soft) | 'clear' (Clear)
  const [gridMode, setGridMode] = useState<'unavailable' | 'preferred' | 'clear'>('unavailable');

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [pRes, rRes] = await Promise.all([
        client.get('/professors'),
        client.get('/rooms')
      ]);
      setProfessors(pRes.data);
      setRooms(rRes.data);
    } catch (err) {
      console.error('Failed to load professors data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (prof?: Professor) => {
    if (prof) {
      setEditingProf(prof);
      setName(prof.name);
      setDepartment(prof.department);
      setPhone(prof.phone || '');
      setEmail(prof.email || '');
      setUnavailableDays(prof.unavailable_days || []);
      setPreferredDays(prof.preferred_days || []);
      setUnavailablePeriods(prof.unavailable_periods || []);
      setPreferredPeriods(prof.preferred_periods || []);
      setUnavailableSlots(prof.unavailable_slots || []);
      setPreferredSlots(prof.preferred_slots || []);
      setFixedRoomId(prof.fixed_room_id || null);
      setUnavailableRoomIds(prof.unavailable_room_ids || []);
      setWeeklyHoursLimit(prof.weekly_hours_limit || 15);
    } else {
      setEditingProf(null);
      setName('');
      setDepartment('컴퓨터공학과');
      setPhone('');
      setEmail('');
      setUnavailableDays([]);
      setPreferredDays([]);
      setUnavailablePeriods([]);
      setPreferredPeriods([]);
      setUnavailableSlots([]);
      setPreferredSlots([]);
      setFixedRoomId(null);
      setUnavailableRoomIds([]);
      setWeeklyHoursLimit(15);
    }
    setGridMode('unavailable');
    setIsModalOpen(true);
  };

  // Header toggles: whole day or whole period
  const handleDayToggle = (day: string, mode: 'unavailable' | 'preferred') => {
    if (mode === 'unavailable') {
      if (unavailableDays.includes(day)) {
        setUnavailableDays(unavailableDays.filter((d) => d !== day));
      } else {
        setUnavailableDays([...unavailableDays, day]);
        setPreferredDays(preferredDays.filter((d) => d !== day));
      }
    } else {
      if (preferredDays.includes(day)) {
        setPreferredDays(preferredDays.filter((d) => d !== day));
      } else {
        setPreferredDays([...preferredDays, day]);
        setUnavailableDays(unavailableDays.filter((d) => d !== day));
      }
    }
  };

  const handlePeriodToggle = (periodId: number, mode: 'unavailable' | 'preferred') => {
    if (mode === 'unavailable') {
      if (unavailablePeriods.includes(periodId)) {
        setUnavailablePeriods(unavailablePeriods.filter((p) => p !== periodId));
      } else {
        setUnavailablePeriods([...unavailablePeriods, periodId]);
        setPreferredPeriods(preferredPeriods.filter((p) => p !== periodId));
      }
    } else {
      if (preferredPeriods.includes(periodId)) {
        setPreferredPeriods(preferredPeriods.filter((p) => p !== periodId));
      } else {
        setPreferredPeriods([...preferredPeriods, periodId]);
        setUnavailablePeriods(unavailablePeriods.filter((p) => p !== periodId));
      }
    }
  };

  // Individual cell click handler (e.g. 월요일 1교시 단일 셀만 토글)
  const handleCellClick = (day: string, periodId: number) => {
    const slotKey = `${day}-${periodId}`;

    if (gridMode === 'unavailable') {
      if (unavailableSlots.includes(slotKey)) {
        setUnavailableSlots(unavailableSlots.filter((s) => s !== slotKey));
      } else {
        setUnavailableSlots([...unavailableSlots, slotKey]);
        setPreferredSlots(preferredSlots.filter((s) => s !== slotKey));
      }
    } else if (gridMode === 'preferred') {
      if (preferredSlots.includes(slotKey)) {
        setPreferredSlots(preferredSlots.filter((s) => s !== slotKey));
      } else {
        setPreferredSlots([...preferredSlots, slotKey]);
        setUnavailableSlots(unavailableSlots.filter((s) => s !== slotKey));
      }
    } else {
      // Clear mode: remove this specific cell
      setUnavailableSlots(unavailableSlots.filter((s) => s !== slotKey));
      setPreferredSlots(preferredSlots.filter((s) => s !== slotKey));
    }
  };

  const handleClearAllConstraints = () => {
    setUnavailableDays([]);
    setPreferredDays([]);
    setUnavailablePeriods([]);
    setPreferredPeriods([]);
    setUnavailableSlots([]);
    setPreferredSlots([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      semester_id: 1,
      name,
      department,
      phone,
      email,
      unavailable_days: unavailableDays,
      preferred_days: preferredDays,
      unavailable_periods: unavailablePeriods,
      preferred_periods: preferredPeriods,
      unavailable_slots: unavailableSlots,
      preferred_slots: preferredSlots,
      fixed_room_id: fixedRoomId || null,
      unavailable_room_ids: unavailableRoomIds,
      weekly_hours_limit: weeklyHoursLimit,
    };

    try {
      if (editingProf) {
        await client.put(`/professors/${editingProf.id}`, payload);
      } else {
        await client.post('/professors', payload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || '교수 정보 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, profName: string) => {
    if (!confirm(`${profName} 교수의 정보를 삭제하시겠습니까?`)) return;
    try {
      await client.delete(`/professors/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || '삭제 실패');
    }
  };

  // Helper for mini preview grid on Professor card
  const renderMiniGrid = (prof: Professor) => {
    const unavailDays = prof.unavailable_days || [];
    const prefDays = prof.preferred_days || [];
    const unavailPeriods = prof.unavailable_periods || [];
    const prefPeriods = prof.preferred_periods || [];
    const unavailSlots = prof.unavailable_slots || [];
    const prefSlots = prof.preferred_slots || [];

    return (
      <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/80 space-y-2">
        <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700 px-0.5">
          <span className="flex items-center space-x-1">
            <Calendar className="w-3.5 h-3.5 text-blue-600" />
            <span>제약조건 시각화 시간표</span>
          </span>
          <div className="flex items-center space-x-2 text-[10px]">
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-red-500 inline-block"></span>
              <span className="text-red-600 font-bold">불가</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-blue-500 inline-block"></span>
              <span className="text-blue-600 font-bold">선호</span>
            </span>
          </div>
        </div>

        <div className="grid grid-cols-6 gap-1 text-[10px] text-center font-medium">
          <div className="bg-slate-200 text-slate-600 py-1 rounded font-bold">교시</div>
          {DAYS.map((d) => (
            <div
              key={d}
              className={`py-1 rounded text-white font-bold transition-all ${
                unavailDays.includes(d)
                  ? 'bg-red-600 shadow-sm'
                  : prefDays.includes(d)
                  ? 'bg-blue-600 shadow-sm'
                  : 'bg-slate-700'
              }`}
            >
              {d}
            </div>
          ))}

          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((p) => (
            <React.Fragment key={p}>
              <div
                className={`py-1 rounded font-bold transition-all ${
                  unavailPeriods.includes(p)
                    ? 'bg-red-100 text-red-700 border border-red-300'
                    : prefPeriods.includes(p)
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {p}
              </div>
              {DAYS.map((d) => {
                const slotKey = `${d}-${p}`;
                const isUnavail = unavailDays.includes(d) || unavailPeriods.includes(p) || unavailSlots.includes(slotKey);
                const isPref = !isUnavail && (prefDays.includes(d) || prefPeriods.includes(p) || prefSlots.includes(slotKey));

                let bgClass = 'bg-white border border-slate-200 text-slate-300';
                if (isUnavail) bgClass = 'bg-red-500 text-white font-bold shadow-xs';
                else if (isPref) bgClass = 'bg-blue-500 text-white font-bold shadow-xs';

                return (
                  <div key={d} className={`py-1 rounded text-center transition-all ${bgClass}`}>
                    {isUnavail ? '✕' : isPref ? '★' : '•'}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2 text-blue-600 font-semibold text-xs mb-1">
            <UserCheck className="w-4 h-4" />
            <span>교수 제약조건 관리</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">교수 정보 및 6대 제약조건 등록/수정</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            개별 시간표 셀(예: 월요일 1교시) 클릭으로 단일 단락 제약조건을 설정하고 요일/교시 헤더로 일괄 설정할 수 있습니다.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-blue-500/20 flex items-center space-x-1.5 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>신규 교수 등록</span>
        </button>
      </div>

      {/* Professor List Cards */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400">
          데이터를 불러오는 중입니다...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {professors.map((p) => {
            const fixedRoom = rooms.find((r) => r.id === p.fixed_room_id);
            const totalUnavailSlots = (p.unavailable_slots || []).length;
            const totalPrefSlots = (p.preferred_slots || []).length;

            return (
              <div
                key={p.id}
                className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-blue-300 transition-all flex flex-col justify-between"
              >
                <div className="space-y-4">
                  {/* Top Profile */}
                  <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-base text-slate-900">{p.name} 교수</span>
                        <span className="bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-bold px-2.5 py-0.5 rounded-full">
                          {p.department}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1 flex items-center space-x-3">
                        <span>{p.email || '이메일 미지정'}</span>
                        {p.phone && <span>• {p.phone}</span>}
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => handleOpenModal(p)}
                        className="p-2 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors flex items-center space-x-1 text-xs font-semibold"
                        title="수정"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>수정</span>
                      </button>
                      <button
                        onClick={() => handleDelete(p.id, p.name)}
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors text-xs"
                        title="삭제"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* 6 Core Constraint Badges Summary */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px] font-semibold flex items-center space-x-1">
                        <Ban className="w-3 h-3 text-red-500" />
                        <span>불가 요일/교시/셀</span>
                      </div>
                      <div className="font-bold text-red-600 mt-0.5">
                        {p.unavailable_days.length > 0 && <span>{p.unavailable_days.map(d => `${d}요일`).join(', ')} (종일) </span>}
                        {p.unavailable_periods.length > 0 && <span>{p.unavailable_periods.map(k => `${k}교시`).join(', ')} </span>}
                        {totalUnavailSlots > 0 && <span>({totalUnavailSlots}개 단일셀)</span>}
                        {p.unavailable_days.length === 0 && p.unavailable_periods.length === 0 && totalUnavailSlots === 0 && '없음'}
                      </div>
                    </div>

                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px] font-semibold flex items-center space-x-1">
                        <Star className="w-3 h-3 text-blue-500" />
                        <span>선호 요일/교시/셀</span>
                      </div>
                      <div className="font-bold text-blue-600 mt-0.5">
                        {p.preferred_days.length > 0 && <span>{p.preferred_days.map(d => `${d}요일`).join(', ')} (종일) </span>}
                        {p.preferred_periods.length > 0 && <span>{p.preferred_periods.map(k => `${k}교시`).join(', ')} </span>}
                        {totalPrefSlots > 0 && <span>({totalPrefSlots}개 단일셀)</span>}
                        {p.preferred_days.length === 0 && p.preferred_periods.length === 0 && totalPrefSlots === 0 && '없음'}
                      </div>
                    </div>

                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px] font-semibold flex items-center space-x-1">
                        <Building className="w-3 h-3 text-emerald-500" />
                        <span>고정 강의실 (Hard)</span>
                      </div>
                      <div className="font-bold text-emerald-600 mt-0.5 truncate">
                        {fixedRoom ? `${fixedRoom.building} ${fixedRoom.name}` : '없음 (자율 배정)'}
                      </div>
                    </div>

                    <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px] font-semibold flex items-center space-x-1">
                        <Clock className="w-3 h-3 text-amber-500" />
                        <span>주당 최대 시수 (Hard)</span>
                      </div>
                      <div className="font-bold text-slate-800 mt-0.5">
                        {p.weekly_hours_limit}시간 / 주
                      </div>
                    </div>
                  </div>

                  {/* Visualized Timetable Grid Preview */}
                  {renderMiniGrid(p)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Professor Form Modal with Visualized Interactive Timetable */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-4xl w-full p-6 my-6 max-h-[92vh] overflow-y-auto space-y-6">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center space-x-2 text-blue-600 font-semibold text-xs mb-0.5">
                  <Sparkles className="w-4 h-4" />
                  <span>단일 셀 / 교시 / 요일별 시각화 제약조건 설정</span>
                </div>
                <h3 className="font-bold text-slate-900 text-xl">
                  {editingProf ? `${editingProf.name} 교수 제약조건 수정` : '신규 교수 등록 및 6대 제약조건 설정'}
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 font-bold flex items-center justify-center transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6 text-xs">
              {/* 기본 인적 사항 */}
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200/80 space-y-3">
                <h4 className="font-bold text-slate-800 text-sm flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <span>교수 기본 정보</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">교수 성함 *</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="예: 홍길동"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">소속 학과 *</label>
                    <input
                      type="text"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="예: 컴퓨터공학과"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">연락처</label>
                    <input
                      type="text"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="010-0000-0000"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">이메일</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="prof@dongseo.ac.kr"
                    />
                  </div>
                </div>
              </div>

              {/* 6대 제약조건 시각화 설정 영역 */}
              <div className="bg-slate-900 text-white p-5 rounded-2xl space-y-4 shadow-xl border border-slate-800">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div>
                    <h4 className="font-bold text-white text-base flex items-center space-x-2">
                      <Calendar className="w-5 h-5 text-blue-400" />
                      <span>6대 제약조건 시각화 시간표 매트릭스</span>
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5">
                      • **개별 셀 클릭**: 월요일 1교시 등 단일 시간 단락만 지정/해제<br/>
                      • **헤더 클릭**: 요일(상단) 또는 교시(좌측) 전체 일괄 토글
                    </p>
                  </div>

                  {/* Mode Toolbar */}
                  <div className="flex items-center space-x-1.5 bg-slate-800 p-1.5 rounded-xl border border-slate-700 shrink-0">
                    <button
                      type="button"
                      onClick={() => setGridMode('unavailable')}
                      className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        gridMode === 'unavailable'
                          ? 'bg-red-600 text-white shadow-md'
                          : 'text-slate-400 hover:text-white hover:bg-slate-700'
                      }`}
                    >
                      <Ban className="w-3.5 h-3.5" />
                      <span>불가(Hard) 모드</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setGridMode('preferred')}
                      className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                        gridMode === 'preferred'
                          ? 'bg-blue-600 text-white shadow-md'
                          : 'text-slate-400 hover:text-white hover:bg-slate-700'
                      }`}
                    >
                      <Star className="w-3.5 h-3.5" />
                      <span>선호(Soft) 모드</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setGridMode('clear')}
                      className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        gridMode === 'clear'
                          ? 'bg-slate-600 text-white shadow-md'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>해제 모드</span>
                    </button>
                  </div>
                </div>

                {/* Legend Bar & Reset */}
                <div className="flex flex-wrap items-center justify-between gap-3 text-xs bg-slate-800/60 px-3.5 py-2 rounded-xl border border-slate-800">
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-1.5">
                      <span className="w-3.5 h-3.5 rounded bg-red-600 text-white flex items-center justify-center font-bold text-[10px]">✕</span>
                      <span className="text-red-400 font-bold">불가 지정셀 / 요일 / 교시 (Hard)</span>
                    </div>
                    <div className="flex items-center space-x-1.5">
                      <span className="w-3.5 h-3.5 rounded bg-blue-600 text-white flex items-center justify-center font-bold text-[10px]">★</span>
                      <span className="text-blue-400 font-bold">선호 지정셀 / 요일 / 교시 (Soft)</span>
                    </div>
                    <div className="flex items-center space-x-1.5">
                      <span className="w-3.5 h-3.5 rounded bg-slate-700 border border-slate-600 inline-block"></span>
                      <span className="text-slate-300">기본 가능</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleClearAllConstraints}
                    className="text-slate-400 hover:text-red-400 text-xs flex items-center space-x-1 font-semibold transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>전체 제약조건 초기화</span>
                  </button>
                </div>

                {/* Interactive Visual Timetable Matrix Grid */}
                <div className="overflow-x-auto">
                  <table className="w-full text-center border-collapse">
                    <thead>
                      <tr>
                        <th className="p-2 bg-slate-800 text-slate-400 text-xs font-semibold rounded-tl-xl border border-slate-700 w-28">
                          교시 \ 요일
                        </th>
                        {DAYS.map((day) => {
                          const isUnavailDay = unavailableDays.includes(day);
                          const isPrefDay = preferredDays.includes(day);

                          let dayHeaderBg = 'bg-slate-800 hover:bg-slate-700 text-slate-200';
                          if (isUnavailDay) dayHeaderBg = 'bg-red-600 text-white font-bold';
                          else if (isPrefDay) dayHeaderBg = 'bg-blue-600 text-white font-bold';

                          return (
                            <th
                              key={day}
                              onClick={() => handleDayToggle(day, gridMode === 'preferred' ? 'preferred' : 'unavailable')}
                              className={`p-2 cursor-pointer transition-all border border-slate-700 select-none ${dayHeaderBg}`}
                              title={`${day}요일 전체 ${gridMode === 'unavailable' ? '불가' : gridMode === 'preferred' ? '선호' : '해제'} 토글`}
                            >
                              <div className="flex items-center justify-center space-x-1">
                                <span>{day}요일</span>
                                {isUnavailDay && <span className="text-[10px]">🚫</span>}
                                {isPrefDay && <span className="text-[10px]">⭐</span>}
                              </div>
                              <div className="text-[9px] font-normal opacity-75 mt-0.5">
                                {isUnavailDay ? '종일 불가' : isPrefDay ? '종일 선호' : '요일 전체토글'}
                              </div>
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {PERIODS.map((period) => {
                        const isUnavailPeriod = unavailablePeriods.includes(period.id);
                        const isPrefPeriod = preferredPeriods.includes(period.id);

                        let periodHeaderBg = 'bg-slate-800 hover:bg-slate-700 text-slate-300';
                        if (isUnavailPeriod) periodHeaderBg = 'bg-red-900/80 text-red-200 border-red-700 font-bold';
                        else if (isPrefPeriod) periodHeaderBg = 'bg-blue-900/80 text-blue-200 border-blue-700 font-bold';

                        return (
                          <tr key={period.id}>
                            <td
                              onClick={() => handlePeriodToggle(period.id, gridMode === 'preferred' ? 'preferred' : 'unavailable')}
                              className={`p-2 border border-slate-700 cursor-pointer transition-all select-none text-left ${periodHeaderBg}`}
                              title={`${period.name} 전체 ${gridMode === 'unavailable' ? '불가' : gridMode === 'preferred' ? '선호' : '해제'} 토글`}
                            >
                              <div className="font-bold flex items-center justify-between text-xs">
                                <span>{period.name}</span>
                                {isUnavailPeriod && <span className="text-[10px] text-red-400">🚫</span>}
                                {isPrefPeriod && <span className="text-[10px] text-blue-400">⭐</span>}
                              </div>
                              <div className="text-[9px] opacity-70 font-mono">{period.time}</div>
                            </td>

                            {DAYS.map((day) => {
                              const slotKey = `${day}-${period.id}`;
                              const isUnavail = unavailableDays.includes(day) || unavailablePeriods.includes(period.id) || unavailableSlots.includes(slotKey);
                              const isPref = !isUnavail && (preferredDays.includes(day) || preferredPeriods.includes(period.id) || preferredSlots.includes(slotKey));

                              let cellBg = 'bg-slate-950 hover:bg-slate-800 border-slate-800 text-slate-500';
                              let cellIcon = null;

                              if (isUnavail) {
                                cellBg = 'bg-red-600 hover:bg-red-500 text-white font-bold border-red-500 shadow-md';
                                cellIcon = <span className="text-xs">🚫 불가</span>;
                              } else if (isPref) {
                                cellBg = 'bg-blue-600 hover:bg-blue-500 text-white font-bold border-blue-500 shadow-md';
                                cellIcon = <span className="text-xs">⭐ 선호</span>;
                              }

                              return (
                                <td
                                  key={day}
                                  onClick={() => handleCellClick(day, period.id)}
                                  className={`p-2.5 border transition-all cursor-pointer select-none text-center h-11 ${cellBg}`}
                                  title={`${day}요일 ${period.name} 클릭 시 단일 셀 토글`}
                                >
                                  {cellIcon || <span className="text-slate-600 text-[10px]">가능</span>}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Live Selected Summary */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-2">
                  <div className="bg-slate-800 p-3 rounded-xl border border-slate-700 space-y-1">
                    <div className="text-red-400 font-bold flex items-center space-x-1.5">
                      <Ban className="w-3.5 h-3.5" />
                      <span>설정된 불가 제약조건 (Hard)</span>
                    </div>
                    <div className="text-slate-300 space-y-0.5">
                      <div>• 불가 종일: <span className="font-bold text-white">{unavailableDays.length > 0 ? unavailableDays.map(d => `${d}요일`).join(', ') : '없음'}</span></div>
                      <div>• 불가 교시: <span className="font-bold text-white">{unavailablePeriods.length > 0 ? unavailablePeriods.map(p => `${p}교시`).join(', ') : '없음'}</span></div>
                      <div>• 불가 단일 셀: <span className="font-bold text-red-300">{unavailableSlots.length > 0 ? unavailableSlots.map(s => s.replace('-', '요일 ')).join(', ') : '없음'}</span></div>
                    </div>
                  </div>

                  <div className="bg-slate-800 p-3 rounded-xl border border-slate-700 space-y-1">
                    <div className="text-blue-400 font-bold flex items-center space-x-1.5">
                      <Star className="w-3.5 h-3.5" />
                      <span>설정된 선호 제약조건 (Soft)</span>
                    </div>
                    <div className="text-slate-300 space-y-0.5">
                      <div>• 선호 종일: <span className="font-bold text-white">{preferredDays.length > 0 ? preferredDays.map(d => `${d}요일`).join(', ') : '없음'}</span></div>
                      <div>• 선호 교시: <span className="font-bold text-white">{preferredPeriods.length > 0 ? preferredPeriods.map(p => `${p}교시`).join(', ') : '없음'}</span></div>
                      <div>• 선호 단일 셀: <span className="font-bold text-blue-300">{preferredSlots.length > 0 ? preferredSlots.map(s => s.replace('-', '요일 ')).join(', ') : '없음'}</span></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 5. 고정 강의실 & 6. 주당 시수 제한 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-2xl border border-slate-200">
                {/* 5. 강의실 픽스 (Hard) */}
                <div>
                  <label className="block font-bold text-emerald-700 mb-1 flex items-center space-x-1">
                    <Building className="w-4 h-4 text-emerald-600" />
                    <span>5. 고정 강의실 지정 (Hard Constraint)</span>
                  </label>
                  <p className="text-[11px] text-slate-500 mb-2">
                    해당 교수의 모든 강의가 특정 강의실에서만 진행되도록 고정합니다.
                  </p>
                  <select
                    value={fixedRoomId || ''}
                    onChange={(e) => setFixedRoomId(e.target.value ? Number(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl outline-none focus:ring-2 focus:ring-emerald-500 bg-white font-medium"
                  >
                    <option value="">고정 강의실 없음 (자율 자동 배정)</option>
                    {rooms.map((r) => (
                      <option key={r.id} value={r.id}>
                        🏢 {r.building} {r.name} (수용 {r.capacity}명 {r.is_computer_lab ? '| 실습실' : ''})
                      </option>
                    ))}
                  </select>
                </div>

                {/* 6. 주당 시수 제한 (Hard) */}
                <div>
                  <label className="block font-bold text-amber-700 mb-1 flex items-center space-x-1">
                    <Clock className="w-4 h-4 text-amber-600" />
                    <span>6. 주당 최대 강의 시수 제한 (Hard Constraint)</span>
                  </label>
                  <p className="text-[11px] text-slate-500 mb-2">
                    교수의 주당 배정 가능한 최대 학점/시수를 제한합니다.
                  </p>
                  <div className="flex items-center space-x-3 bg-white p-2.5 border border-slate-300 rounded-xl">
                    <input
                      type="range"
                      min="6"
                      max="30"
                      step="1"
                      value={weeklyHoursLimit}
                      onChange={(e) => setWeeklyHoursLimit(Number(e.target.value))}
                      className="flex-1 accent-amber-600 cursor-pointer"
                    />
                    <div className="flex items-center space-x-1 bg-amber-50 border border-amber-200 px-3 py-1 rounded-lg">
                      <span className="font-bold text-amber-800 text-sm">{weeklyHoursLimit}</span>
                      <span className="text-amber-700 text-xs font-semibold">시간 / 주</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-200">
                <div className="text-slate-400 text-xs flex items-center space-x-1">
                  <Info className="w-4 h-4 text-blue-500" />
                  <span>단일 셀 제약조건도 자동 시간표 배정 솔버에 즉시 반영됩니다.</span>
                </div>
                <div className="flex space-x-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-5 py-2.5 font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-6 py-2.5 font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-lg shadow-blue-500/20 disabled:opacity-50 transition-all flex items-center space-x-1.5"
                  >
                    <Check className="w-4 h-4" />
                    <span>{saving ? '저장 중...' : editingProf ? '제약조건 수정 완료' : '신규 교수 등록'}</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfessorsPage;
