import client from './api/client';
import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import ProfessorsPage from './pages/ProfessorsPage';
import RoomsPage from './pages/RoomsPage';
import CoursesPage from './pages/CoursesPage';
import ComparePage from './pages/ComparePage';
import TimetableViewPage from './pages/TimetableViewPage';
import LogsPage from './pages/LogsPage';
import LoginPage from './pages/LoginPage';

export function App() {
  const [user, setUser] = useState<any>(null);
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [hasError, setHasError] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await client.get('/auth/me');
        if (res.data) {
          setUser(res.data);
          localStorage.setItem('user', JSON.stringify(res.data));
          localStorage.setItem('token', 'cookie-session');
        }
      } catch (err) {
        console.error('Session check failed', err);
        handleLogout();
      }
    };
    
    checkSession();
  }, []);
  const handleLogout = async () => {
    try {
      await client.post('/auth/logout');
    } catch(e) {
      console.error(e);
    }
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    setUser(null);
  };


  if (hasError) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white p-6 rounded-2xl shadow-xl max-w-lg w-full border border-red-200">
          <h2 className="text-xl font-bold text-red-600 mb-2">화면 렌더링 오류 발생</h2>
          <p className="text-sm text-slate-600 mb-4">현재 화면을 표시하는 도중 예기치 않은 오류가 발생했습니다. 개발자에게 문의해주세요.</p>
          <pre className="bg-red-50 text-red-800 p-4 rounded-xl text-xs overflow-auto max-h-64 whitespace-pre-wrap">{errorMsg}</pre>
          <button 
            onClick={() => { setHasError(false); setCurrentTab('dashboard'); }}
            className="mt-4 px-4 py-2 bg-slate-900 text-white rounded-lg text-sm hover:bg-slate-800 w-full"
          >
            대시보드로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLoginSuccess={(userData) => setUser(userData)} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-['Pretendard',sans-serif]">
      <Header user={user} onLogout={handleLogout} />

      <div className="flex flex-1">
        <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full">
          {currentTab === 'dashboard' && <DashboardPage onSelectTab={setCurrentTab} />}
          {currentTab === 'professors' && <ProfessorsPage />}
          {currentTab === 'rooms' && <RoomsPage />}
          {currentTab === 'courses' && <CoursesPage />}
          {currentTab === 'compare' && <ComparePage />}
          {currentTab === 'view' && <TimetableViewPage />}
          {currentTab === 'logs' && <LogsPage />}
        </main>
      </div>
    </div>
  );
}

export default App;
