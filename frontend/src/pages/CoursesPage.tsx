import React, { useEffect, useState } from 'react';
import { BookOpen, Plus, Edit2, Trash2, Monitor, Users, User } from 'lucide-react';
import { Course, Professor, Room } from '../types';
import client from '../api/client';

const CoursesPage: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);

  // Form fields
  const [name, setName] = useState('');
  const [professorId, setProfessorId] = useState<number>(0);
  const [department, setDepartment] = useState('컴퓨터공학과');
  const [grade, setGrade] = useState<number>(1);
  const [section, setSection] = useState('A');
  const [weeklyHours, setWeeklyHours] = useState<number>(3);
  const [expectedStudents, setExpectedStudents] = useState<number>(30);
  const [computerRequired, setComputerRequired] = useState<boolean>(false);
  const [fixedRoomId, setFixedRoomId] = useState<number | null>(null);

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cRes, pRes, rRes] = await Promise.all([
        client.get('/courses'),
        client.get('/professors'),
        client.get('/rooms')
      ]);
      setCourses(cRes.data);
      setProfessors(pRes.data);
      setRooms(rRes.data);
      if (pRes.data.length > 0 && !professorId) {
        setProfessorId(pRes.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch courses data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (course?: Course) => {
    if (course) {
      setEditingCourse(course);
      setName(course.name);
      setProfessorId(course.professor_id);
      setDepartment(course.department);
      setGrade(course.grade);
      setSection(course.section);
      setWeeklyHours(course.weekly_hours);
      setExpectedStudents(course.expected_students);
      setComputerRequired(course.computer_required);
      setFixedRoomId(course.fixed_room_id || null);
    } else {
      setEditingCourse(null);
      setName('');
      setProfessorId(professors.length > 0 ? professors[0].id : 0);
      setDepartment('컴퓨터공학과');
      setGrade(1);
      setSection('A');
      setWeeklyHours(3);
      setExpectedStudents(30);
      setComputerRequired(false);
      setFixedRoomId(null);
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      semester_id: 1,
      name,
      professor_id: professorId,
      department,
      grade,
      section,
      weekly_hours: weeklyHours,
      expected_students: expectedStudents,
      computer_required: computerRequired,
      fixed_room_id: fixedRoomId || null,
    };

    try {
      if (editingCourse) {
        await client.put(`/courses/${editingCourse.id}`, payload);
      } else {
        await client.post('/courses', payload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || '강의 정보 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, cName: string) => {
    if (!confirm(`${cName} 강의를 삭제하시겠습니까?`)) return;
    try {
      await client.delete(`/courses/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || '삭제 실패');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2 text-indigo-600 font-semibold text-xs mb-1">
            <BookOpen className="w-4 h-4" />
            <span>강의 정보 관리</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">개설 강의 및 컴퓨터 필요 여부 관리</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            과목명, 담당교수, 소속 학과, 학년/분반, 시수 및 컴퓨터 필요 여부(Hard HC-07)를 설정합니다.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4 py-2.5 rounded-xl shadow-md shadow-indigo-500/20 flex items-center space-x-1.5 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>신규 강의 등록</span>
        </button>
      </div>

      {/* Courses Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {courses.map((c) => (
          <div key={c.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-indigo-300 transition-all">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-base text-slate-900">{c.name}</span>
                  {c.computer_required && (
                    <span className="bg-cyan-100 text-cyan-800 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center space-x-1">
                      <Monitor className="w-3 h-3" />
                      <span>컴퓨터 필수</span>
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5 flex items-center space-x-1">
                  <User className="w-3 h-3" />
                  <span>{c.professor_name} 교수</span>
                </div>
              </div>

              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleOpenModal(c)}
                  className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(c.id, c.name)}
                  className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-600">
              <div className="flex items-center justify-between">
                <span>소속 / 학년:</span>
                <span className="font-semibold text-slate-900">
                  {c.department} {c.grade}학년 ({c.section}분반)
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span>주당 시수 / 수강예상:</span>
                <span className="font-semibold text-slate-900">
                  {c.weekly_hours}시간 / {c.expected_students}명
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Course Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <h3 className="font-bold text-slate-900 text-base">{editingCourse ? '강의 정보 수정' : '신규 강의 등록'}</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600 font-bold">
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">과목명 *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="e.g., 알고리즘개론"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">담당 교수 *</label>
                <select
                  value={professorId}
                  onChange={(e) => setProfessorId(Number(e.target.value))}
                  required
                  className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                >
                  {professors.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} 교수 ({p.department})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">소속 학과</label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    required
                    className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">학년 / 분반</label>
                  <div className="flex gap-2">
                    <select
                      value={grade}
                      onChange={(e) => setGrade(Number(e.target.value))}
                      className="w-1/2 px-2 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      {[1, 2, 3, 4].map((g) => (
                        <option key={g} value={g}>
                          {g}학년
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                      className="w-1/2 px-2 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 text-center"
                      placeholder="분반"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">주당 시수 (시간)</label>
                  <input
                    type="number"
                    value={weeklyHours}
                    onChange={(e) => setWeeklyHours(Number(e.target.value))}
                    required
                    min={1}
                    max={6}
                    className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">예상 수강 인원</label>
                  <input
                    type="number"
                    value={expectedStudents}
                    onChange={(e) => setExpectedStudents(Number(e.target.value))}
                    required
                    min={5}
                    className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="pt-2">
                <label className="flex items-center space-x-2 cursor-pointer bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <input
                    type="checkbox"
                    checked={computerRequired}
                    onChange={(e) => setComputerRequired(e.target.checked)}
                    className="w-4 h-4 text-indigo-600 rounded"
                  />
                  <div>
                    <span className="font-bold text-slate-800">컴퓨터 필수 수업 (Hard Constraint)</span>
                    <p className="text-[10px] text-slate-500">체크 시 컴퓨터실(is_computer_lab=True) 강의실로만 자동 배정됩니다.</p>
                  </div>
                </label>
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
                  className="px-4 py-2 font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-md disabled:opacity-50"
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

export default CoursesPage;
