import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, Users, FileSignature, Briefcase } from 'lucide-react';
import client from '../api/client';
import { Professor } from '../types';

export default function ProfessorsPage() {
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProf, setEditingProf] = useState<Professor | null>(null);

  // Basic Info State
  const [name, setName] = useState('');
  const [employeeNumber, setEmployeeNumber] = useState('');
  const [department, setDepartment] = useState('컴퓨터공학과');

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const pRes = await client.get('/professors');
      setProfessors(pRes.data);
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
      setEmployeeNumber(prof.employee_number || '');
      setDepartment(prof.department);
    } else {
      setEditingProf(null);
      setName('');
      setEmployeeNumber('');
      setDepartment('컴퓨터공학과');
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      name,
      employee_number: employeeNumber,
      department,
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
      const detail = err.response?.data?.detail;
      alert(typeof detail === 'string' ? detail : JSON.stringify(detail) || '저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, pName: string) => {
    if (!confirm(`${pName} 교수님을 삭제하시겠습니까?\n(해당 교수님이 배정된 강의가 있으면 삭제되지 않을 수 있습니다)`)) return;
    try {
      await client.delete(`/professors/${id}`);
      fetchData();
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
      {/* Header */}
      <div className="flex justify-between items-end bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <div className="flex items-center space-x-2 text-indigo-600 mb-1">
            <Users className="w-5 h-5" />
            <span>교수 정보 관리</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">교수 정보 등록 및 관리</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            이름, 사번, 소속 학과 등 기본 정보를 설정합니다.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-indigo-500/20 flex items-center space-x-1.5 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>신규 교수 등록</span>
        </button>
      </div>

      {/* Professor List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {professors.map((p) => (
          <div key={p.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-indigo-300 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between border-b border-slate-100 pb-3 mb-3">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 font-bold text-lg">
                    {p.name.charAt(0)}
                  </div>
                  <div>
                    <span className="font-bold text-base text-slate-900">{p.name} 교수</span>
                    <div className="text-xs text-slate-500 mt-0.5">{p.department}</div>
                  </div>
                </div>

                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleOpenModal(p)}
                    className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(p.id, p.name)}
                    className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="space-y-2 text-xs text-slate-600">
                <div className="flex items-center space-x-2">
                  <FileSignature className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-semibold text-slate-700 w-12">사번</span>
                  <span>{p.employee_number || '미입력'}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Briefcase className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-semibold text-slate-700 w-12">소속</span>
                  <span>{p.department}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-sm w-full p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h3 className="font-bold text-slate-900 text-base">
                {editingProf ? `${editingProf.name} 교수 정보 수정` : '신규 교수 등록'}
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">성함 *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 홍길동"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">사번 *</label>
                <input
                  type="text"
                  value={employeeNumber}
                  onChange={(e) => setEmployeeNumber(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 20240001"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">소속 학과 *</label>
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
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
