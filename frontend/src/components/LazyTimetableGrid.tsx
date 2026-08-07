import React, { useState, useEffect, useRef } from 'react';
import TimetableGrid from './TimetableGrid';

const LazyTimetableGrid = (props: any) => {
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            // Once visible, we can stop observing if we want to keep it rendered
            observer.disconnect();
          }
        });
      },
      { rootMargin: '200px' } // Pre-load slightly before scrolling into view
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} style={{ minHeight: '600px' }}>
      {isVisible ? (
        <TimetableGrid {...props} />
      ) : (
        <div className="flex items-center justify-center h-full h-96 text-slate-400 bg-slate-50 animate-pulse rounded-2xl">
          <span className="font-semibold text-sm">시간표 렌더링 중...</span>
        </div>
      )}
    </div>
  );
};

export default LazyTimetableGrid;
