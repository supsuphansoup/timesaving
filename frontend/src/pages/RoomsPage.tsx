import React, { useEffect, useState } from 'react';
import { Building2, Plus, Edit2, Trash2, Monitor, Users, Ban } from 'lucide-react';
import { Room } from '../types';
import client from '../api/client';

const DAYS = ['월', '화', '수', '목', '금'];
const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

const RoomsPage: React.FC = () => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);

  // Form Fields
  const [name, setName] = useState('');
  const [building, setBuilding] = useState('뉴밀레니엄관');
  const [capacity, setCapacity] = useState(40);
  const [isComputerLab, setIsComputerLab] = useState(false);
  const [isCommon, setIsCommon] = useState(false);
  const [notes, setNotes] = useState('');
  const [unavailableHours, setUnavailableHours] = useState<{ day: string; periods: number[] }[]>([]);

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchRooms();
  }, []);

  const fetchRooms = async () => {
    setLoading(true);
    try {
      const res = await client.get('/rooms');
      setRooms(res.data);
    } catch (err) {
      console.error('Failed to fetch rooms', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (room?: Room) => {
    if (room) {
      setEditingRoom(room);
      setName(room.name);
      setBuilding(room.building);
      setCapacity(room.capacity);
      setIsComputerLab(room.is_computer_lab);
      setIsCommon(room.is_common);
      setNotes(room.notes || '');
      setUnavailableHours(room.unavailable_hours || []);
    } else {
      setEditingRoom(null);
      setName('');
      setBuilding('뉴밀레니엄관');
      setCapacity(40);
      setIsComputerLab(false);
      setIsCommon(false);
      setNotes('');
      setUnavailableHours([]);
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      name,
      building,
      capacity,
      is_computer_lab: isComputerLab,
      is_common: isCommon,
      notes,
      unavailable_hours: unavailableHours,
    };

    try {
      if (editingRoom) {
        await client.put(`/rooms/${editingRoom.id}`, payload);
      } else {
        await client.post('/rooms', payload);
      }
      setIsModalOpen(false);
      fetchRooms();
    } catch (err: any) {
      alert(err.response?.data?.detail || '강의실 정보 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, rName: string) => {
    if (!confirm(`${rName} 강의실을 삭제하시겠습니까?`)) return;
    try {
      await client.delete(`/rooms/${id}`);
      fetchRooms();
    } catch (err: any) {
      alert(err.response?.data?.detail || '삭제 실패');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2 text-emerald-600 font-semibold text-xs mb-1">
            <Building2 className="w-4 h-4" />
            <span>강의실 정보 관리</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">강의실 조건 및 사용가능/불가 시간 관리</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            강의실별 수용 인원, 컴퓨터실 여부(Hard HC-07), 공용 강의실 여부 및 불가 시간대를 설정합니다.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-emerald-500/20 flex items-center space-x-1.5 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>신규 강의실 등록</span>
        </button>
      </div>

      {/* Room Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rooms.map((r) => (
          <div key={r.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-emerald-300 transition-all">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-base text-slate-900">{r.name}</span>
                  {r.is_computer_lab && (
                    <span className="bg-cyan-100 text-cyan-800 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center space-x-1">
                      <Monitor className="w-3 h-3" />
                      <span>컴퓨터실</span>
                    </span>
                  )}
                  {r.is_common && (
                    <span className="bg-purple-100 text-purple-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                      공용
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">{r.building}</div>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleOpenModal(r)}
                  className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(r.id, r.name)}
                  className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-600">
              <div className="flex items-center justify-between">
                <span className="flex items-center space-x-1">
                  <Users className="w-4 h-4 text-slate-400" />
                  <span>수용 인원:</span>
                </span>
                <span className="font-bold text-slate-900">{r.capacity}명</span>
              </div>

              <div className="flex items-center justify-between">
                <span>비고:</span>
                <span className="font-medium text-slate-700">{r.notes || '없음'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Room Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h3 className="font-bold text-slate-900 text-base">{editingRoom ? '강의실 정보 수정' : '신규 강의실 등록'}</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">건물명 (위치) *</label>
                <input
                  type="text"
                  value={building}
                  onChange={(e) => setBuilding(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., 뉴밀레니엄관"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">강의실명 *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., NM-301"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">수용 인원 *</label>
                <input
                  type="number"
                  value={capacity}
                  onChange={(e) => setCapacity(Number(e.target.value))}
                  required
                  min={10}
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex items-center space-x-6 pt-2">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isComputerLab}
                    onChange={(e) => setIsComputerLab(e.target.checked)}
                    className="w-4 h-4 text-emerald-600 rounded"
                  />
                  <span className="font-semibold text-slate-800">컴퓨터실 여부</span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isCommon}
                    onChange={(e) => setIsCommon(e.target.checked)}
                    className="w-4 h-4 text-emerald-600 rounded"
                  />
                  <span className="font-semibold text-slate-800">공용 강의실 여부</span>
                </label>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">비고</label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="특이사항 메모"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md disabled:opacity-50"
                >
                  {saving ? '저장 중...' : '저장'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoomsPage;
