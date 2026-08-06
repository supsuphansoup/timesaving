import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Users, Monitor, Building } from 'lucide-react';
import client from '../api/client';

export interface Room {
  id: number;
  room_name: string;
  location: string | null;
  capacity: number;
  is_computer_room: boolean;
  is_common_room: boolean;
  remarks: string | null;
}

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);

  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [capacity, setCapacity] = useState<number>(30);
  const [isComputerLab, setIsComputerLab] = useState(false);
  const [isCommon, setIsCommon] = useState(false);
  const [remarks, setRemarks] = useState('');

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
      setName(room.room_name);
      setLocation(room.location || '');
      setCapacity(room.capacity);
      setIsComputerLab(room.is_computer_room);
      setIsCommon(room.is_common_room);
      setRemarks(room.remarks || '');
    } else {
      setEditingRoom(null);
      setName('');
      setLocation('U-IT관');
      setCapacity(30);
      setIsComputerLab(false);
      setIsCommon(false);
      setRemarks('');
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      room_name: name,
      location,
      capacity,
      is_computer_room: isComputerLab,
      is_common_room: isCommon,
      remarks,
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
      const detail = err.response?.data?.detail;
      alert(typeof detail === 'string' ? detail : JSON.stringify(detail) || '강의실 정보 저장에 실패했습니다.');
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <div className="flex items-center space-x-2 text-indigo-600 mb-1">
            <Building className="w-5 h-5" />
            <span>강의실 정보 관리</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">사용 가능한 강의실 관리</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            강의실 호실, 건물, 수용 인원 및 컴퓨터실 여부를 설정합니다.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-indigo-500/20 flex items-center space-x-1.5 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>신규 강의실 등록</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rooms.map((r) => (
          <div key={r.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-indigo-300 transition-all">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center space-x-3 mb-2">
                  <span className="font-bold text-base text-slate-900">{r.room_name}</span>
                  {r.is_computer_room && (
                    <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center space-x-1">
                      <Monitor className="w-3 h-3" />
                      <span>컴퓨터실</span>
                    </span>
                  )}
                  {r.is_common_room && (
                    <span className="bg-purple-100 text-purple-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                      공용
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">{r.location}</div>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleOpenModal(r)}
                  className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(r.id, r.room_name)}
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
                <span className="font-medium text-slate-700">{r.remarks || '없음'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

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
                <label className="block font-semibold text-slate-700 mb-1">호실 명 *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., U-IT 601호"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">건물명</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g., U-IT관"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">수용 인원 *</label>
                  <input
                    type="number"
                    value={capacity}
                    onChange={(e) => setCapacity(Number(e.target.value))}
                    min="1"
                    required
                    className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <label className="flex items-center space-x-2 cursor-pointer bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                  <input
                    type="checkbox"
                    checked={isComputerLab}
                    onChange={(e) => setIsComputerLab(e.target.checked)}
                    className="w-4 h-4 text-indigo-600 rounded"
                  />
                  <div>
                    <span className="font-bold text-slate-800">컴퓨터실 여부</span>
                    <p className="text-[10px] text-slate-500">컴퓨터 실습이 필요한 과목만 배정됩니다.</p>
                  </div>
                </label>
                
                <label className="flex items-center space-x-2 cursor-pointer bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                  <input
                    type="checkbox"
                    checked={isCommon}
                    onChange={(e) => setIsCommon(e.target.checked)}
                    className="w-4 h-4 text-indigo-600 rounded"
                  />
                  <div>
                    <span className="font-bold text-slate-800">공용 강의실 여부</span>
                    <p className="text-[10px] text-slate-500">타 학과와 공동으로 사용하는 강의실입니다.</p>
                  </div>
                </label>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">비고 (선택)</label>
                <input
                  type="text"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="추가 설명..."
                />
              </div>

              <div className="pt-4 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl font-semibold transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all disabled:opacity-50"
                >
                  {saving ? '저장 중...' : '저장하기'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
