import React, { useEffect, useState, useRef } from 'react';
import { CalendarDays, Download, Printer, Filter, Search, Building2, User, BookOpen, Layers } from 'lucide-react';
import { Candidate, Assignment, Room, Professor } from '../types';
import TimetableGrid from '../components/TimetableGrid';
import client from '../api/client';

import * as XLSX from 'xlsx';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

type ViewMode = 'ROOM' | 'PROFESSOR' | 'GRADE' | 'DEPARTMENT';

const TimetableViewPage: React.FC = () => {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter View States
  const [viewMode, setViewMode] = useState<ViewMode>('ROOM');
  const [selectedRoomId, setSelectedRoomId] = useState<number | 'ALL'>('ALL');
  const [selectedProfessorId, setSelectedProfessorId] = useState<number | 'ALL'>('ALL');
  const [selectedGrade, setSelectedGrade] = useState<number | 'ALL'>('ALL');
  const [selectedDepartment, setSelectedDepartment] = useState<string | 'ALL'>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const timetableContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [candRes, rRes, pRes] = await Promise.all([
        client.get('/timetables/candidates'),
        client.get('/rooms'),
        client.get('/professors'),
      ]);

      setRooms(rRes.data);
      setProfessors(pRes.data);

      // Prefer confirmed timetable first, else latest candidate
      
      const confirmed = candRes.data.find((c: any) => c.status === 'CONFIRMED');
      const targetCand = confirmed || (candRes.data.length > 0 ? candRes.data[0] : null);
      
      if (targetCand) {
        const detailRes = await client.get(`/timetables/${targetCand.id}`);
        setCandidate(detailRes.data);
      }

    } catch (err) {
      console.error('Failed to fetch timetable view data', err);
    } finally {
      setLoading(false);
    }
  };

  // Filter assignments based on viewMode and search
  const getFilteredAssignments = (): Assignment[] => {
    if (!candidate) return [];
    let list = candidate.assignments || [];

    if (viewMode === 'ROOM' && selectedRoomId !== 'ALL') {
      list = list.filter((a) => a.room_id === Number(selectedRoomId));
    } else if (viewMode === 'PROFESSOR' && selectedProfessorId !== 'ALL') {
      list = list.filter((a) => a.professor_id === Number(selectedProfessorId));
    } else if (viewMode === 'GRADE' && selectedGrade !== 'ALL') {
      list = list.filter((a) => a.grade === Number(selectedGrade));
    } else if (viewMode === 'DEPARTMENT' && selectedDepartment !== 'ALL') {
      list = list.filter((a) => a.department === selectedDepartment);
    }

    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      list = list.filter(
        (a) =>
          a.course_name.toLowerCase().includes(term) ||
          a.professor_name.toLowerCase().includes(term) ||
          a.room_name.toLowerCase().includes(term) ||
          a.department.toLowerCase().includes(term)
      );
    }

    return list;
  };

  // Excel Export (.xlsx)
  const handleExportExcel = () => {
    const list = getFilteredAssignments();
    const excelData = list.map((a) => ({
      '과목명': a.course_name,
      '담당교수': a.professor_name,
      '소속학과': a.department,
      '학년/분반': `${a.grade}학년 (${a.section}분반)`,
      '강의실': `${a.building} ${a.room_name}`,
      '컴퓨터실여부': a.is_computer_lab ? '예' : '아니오',
      '요일': `${a.day}요일`,
      '시간': `${a.start_period}교시 (${a.duration}시간)`
    }));

    const worksheet = XLSX.utils.json_to_sheet(excelData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, '시간표');
    XLSX.writeFile(workbook, `동서대학교_시간표_${viewMode}_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  const filteredAssignments = getFilteredAssignments();

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="no-print bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-indigo-600 font-semibold text-xs mb-1">
            <CalendarDays className="w-4 h-4" />
            <span>시간표 다각도 조회 & Excel 출력</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            시간표 조회 (강의실별 / 교수별 / 학년별 / 학과별)
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            필터 및 검색 기능으로 시간표를 빠르게 조회하고 Excel로 내보냅니다.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={handleExportExcel}
            className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-3.5 py-2 rounded-xl shadow-md shadow-emerald-500/20 flex items-center space-x-1.5 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Excel 내보내기</span>
          </button>
        </div>
      </div>

      {/* Filter Options Bar */}
      <div className="no-print bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        {/* View Mode Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-slate-100 pb-3">
          <button
            onClick={() => setViewMode('ROOM')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${viewMode === 'ROOM'
                ? 'bg-blue-600 text-white shadow'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
          >
            <Building2 className="w-4 h-4" />
            <span>강의실별 전체 시간표</span>
          </button>

          <button
            onClick={() => setViewMode('PROFESSOR')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${viewMode === 'PROFESSOR'
                ? 'bg-blue-600 text-white shadow'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
          >
            <User className="w-4 h-4" />
            <span>교수별 개별 시간표</span>
          </button>

          <button
            onClick={() => setViewMode('GRADE')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${viewMode === 'GRADE'
                ? 'bg-blue-600 text-white shadow'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>학년별 시간표</span>
          </button>

          <button
            onClick={() => setViewMode('DEPARTMENT')}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all ${viewMode === 'DEPARTMENT'
                ? 'bg-blue-600 text-white shadow'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
          >
            <Layers className="w-4 h-4" />
            <span>학과별 시간표</span>
          </button>
        </div>

        {/* Dropdown Filters & Search */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          {viewMode === 'ROOM' && (
            <div>
              <label className="block font-semibold text-slate-700 mb-1">강의실 필터</label>
              <select
                value={selectedRoomId}
                onChange={(e) => setSelectedRoomId(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="ALL">전체 강의실</option>
                {rooms.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.building} {r.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {viewMode === 'PROFESSOR' && (
            <div>
              <label className="block font-semibold text-slate-700 mb-1">교수 필터</label>
              <select
                value={selectedProfessorId}
                onChange={(e) => setSelectedProfessorId(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="ALL">전체 교수</option>
                {professors.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} 교수 ({p.department})
                  </option>
                ))}
              </select>
            </div>
          )}

          {viewMode === 'GRADE' && (
            <div>
              <label className="block font-semibold text-slate-700 mb-1">학년 필터</label>
              <select
                value={selectedGrade}
                onChange={(e) => setSelectedGrade(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="ALL">전체 학년</option>
                {[1, 2, 3, 4].map((g) => (
                  <option key={g} value={g}>
                    {g}학년
                  </option>
                ))}
              </select>
            </div>
          )}

          {viewMode === 'DEPARTMENT' && (
            <div>
              <label className="block font-semibold text-slate-700 mb-1">학과 필터</label>
              <select
                value={selectedDepartment}
                onChange={(e) => setSelectedDepartment(e.target.value)}
                className="w-full px-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="ALL">전체 학과</option>
                <option value="컴퓨터공학과">컴퓨터공학과</option>
                <option value="정보통신공학과">정보통신공학과</option>
                <option value="AI학부">AI학부</option>
                <option value="디자인학부">디자인학부</option>
                <option value="게임공학과">게임공학과</option>
                <option value="데이터승인학과">데이터승인학과</option>
              </select>
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-700 mb-1">통합 검색 (과목/교수/강의실)</label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="검색어 입력..."
              />
            </div>
          </div>
        </div>
      </div>

      {/* Printable Grid Section */}
      <div ref={timetableContainerRef} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-lg">
              동서대학교 2026학년도 2학기 시간표
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              조회 조건: {viewMode} 기준 | 총 {filteredAssignments.length}개 개설 강의 배정됨
            </p>
          </div>

          {candidate && (
            <span className="text-xs font-semibold px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-200">
              {candidate.name} ({candidate.status === 'CONFIRMED' ? '최종 확정' : '추천안'})
            </span>
          )}
        </div>

        <TimetableGrid assignments={filteredAssignments} readOnly={true} />
      </div>
    </div>
  );
};

export default TimetableViewPage;
