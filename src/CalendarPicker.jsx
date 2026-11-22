import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Lock } from 'lucide-react';

export default function CalendarPicker({ selectedDate, onSelectDate }) {
  // Normalize today at midnight local time
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Maximum allowed date: today + 7 days
  const maxDate = new Date(today);
  maxDate.setDate(today.getDate() + 7);

  const parseYMD = (str) => {
    if (!str) return null;
    const parts = String(str).split('-').map(Number);
    if (parts.length === 3 && !isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
      return new Date(parts[0], parts[1] - 1, parts[2]);
    }
    return new Date(str);
  };

  // View state for navigating months (if the 7-day window spans month boundary)
  const initialDate = selectedDate ? (parseYMD(selectedDate) || today) : today;
  const [viewYear, setViewYear] = useState(initialDate.getFullYear());
  const [viewMonth, setViewMonth] = useState(initialDate.getMonth());

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear(viewYear - 1);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear(viewYear + 1);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  const formatYMD = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const todayStr = formatYMD(today);
  const maxDateStr = formatYMD(maxDate);

  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstDayOfWeek = new Date(viewYear, viewMonth, 1).getDay();

  const cells = [];
  for (let i = 0; i < firstDayOfWeek; i++) {
    cells.push(null);
  }
  for (let dayNum = 1; dayNum <= daysInMonth; dayNum++) {
    const d = new Date(viewYear, viewMonth, dayNum);
    d.setHours(0, 0, 0, 0);
    cells.push(d);
  }

  return (
    <div className="bg-[#FAF8F5] border border-[#E5E0D8] rounded-xl p-3.5 space-y-2.5 select-none">
      <div className="flex items-center justify-between pb-1 border-b border-[#E5E0D8]/60">
        <div className="flex items-center gap-2">
          <CalendarIcon className="w-4 h-4 text-[#3F513D]" />
          <span className="text-xs font-bold text-[#2C352B]">
            {monthNames[viewMonth]} {viewYear}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={prevMonth}
            className="p-1 hover:bg-[#EFECE6] rounded-md text-[#556153] transition"
            title="Previous month"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={nextMonth}
            className="p-1 hover:bg-[#EFECE6] rounded-md text-[#556153] transition"
            title="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-semibold text-[#6B7569]">
        <span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span>
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((d, index) => {
          if (!d) {
            return <div key={`empty-${index}`} className="h-8" />;
          }

          const dateStr = formatYMD(d);
          const isSelectable = d >= today && d <= maxDate;
          const isSelected = selectedDate === dateStr;
          const isToday = dateStr === todayStr;

          return (
            <button
              key={dateStr}
              type="button"
              disabled={!isSelectable}
              onClick={() => {
                if (isSelectable) onSelectDate(dateStr);
              }}
              title={
                !isSelectable
                  ? d < today
                    ? 'Past date cannot be scheduled'
                    : 'Beyond 7-day limit (locked)'
                  : isToday
                  ? 'Today'
                  : dateStr
              }
              className={`h-8 rounded-lg text-xs flex flex-col items-center justify-center relative transition font-medium ${
                isSelected
                  ? 'bg-[#3F513D] text-white font-bold shadow-sm ring-2 ring-[#2D3A2C]'
                  : isSelectable
                  ? 'text-[#2C352B] bg-white border border-[#E5E0D8]/60 hover:bg-[#E2EBDD] hover:text-[#2E542B] hover:border-[#B2C9B0]'
                  : 'text-[#C5BEB5] bg-[#FAF8F5] cursor-not-allowed opacity-35'
              }`}
            >
              <span>{d.getDate()}</span>
              {isToday && !isSelected && (
                <span className="w-1 h-1 rounded-full bg-[#3F513D] absolute bottom-0.5" />
              )}
              {!isSelectable && d > maxDate && (
                <Lock className="w-2 h-2 text-[#C5BEB5] absolute top-0.5 right-0.5 opacity-60" />
              )}
            </button>
          );
        })}
      </div>

      {/* 7-Day Window Guidance Banner */}
      <div className="pt-2 border-t border-[#E5E0D8] flex items-center justify-between text-[11px] text-[#6B7569]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#3F513D]" />
          <span>7-Day Allowed Window: <strong>{todayStr}</strong> → <strong>{maxDateStr}</strong></span>
        </span>
        <span className="font-semibold text-[#3F513D]">
          {selectedDate ? selectedDate : 'None selected'}
        </span>
      </div>
    </div>
  );
}
