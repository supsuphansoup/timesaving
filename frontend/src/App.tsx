import React, { useState } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import ProfessorsPage from './pages/ProfessorsPage';
import RoomsPage from './pages/RoomsPage';
import CoursesPage from './pages/CoursesPage';
import GeneratePage from './pages/GeneratePage';
import ComparePage from './pages/ComparePage';
import TimetableViewPage from './pages/TimetableViewPage';
import LogsPage from './pages/LogsPage';

export function App() {
  const [user] = useState<any>({ username: 'admin', name: '김조교 (컴공과)', role: 'TA' });
  const [currentTab, setCurrentTab] = useState<string>('dashboard');

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-['Pretendard',sans-serif]">
      <Header user={user} />

      <div className="flex flex-1">
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full">
          {currentTab === 'dashboard' && <DashboardPage onSelectTab={setCurrentTab} />}
          {currentTab === 'professors' && <ProfessorsPage />}
          {currentTab === 'rooms' && <RoomsPage />}
          {currentTab === 'courses' && <CoursesPage />}
          {currentTab === 'generate' && <GeneratePage onSelectTab={setCurrentTab} />}
          {currentTab === 'compare' && <ComparePage />}
          {currentTab === 'view' && <TimetableViewPage />}
          {currentTab === 'logs' && <LogsPage />}
        </main>
      </div>
    </div>
  );
}

export default App;
