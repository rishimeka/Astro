'use client';

import { useState } from 'react';
import styles from './DateRangeFilter.module.scss';

export type DateRangePreset = 'all' | 'today' | 'week' | 'month' | 'custom';

export interface DateRange {
  start: Date | null;
  end: Date | null;
}

export interface DateRangeFilterProps {
  preset: DateRangePreset;
  customRange?: DateRange;
  onChange: (preset: DateRangePreset, range?: DateRange) => void;
}

const presetConfig: Record<DateRangePreset, { label: string }> = {
  all: { label: 'All Time' },
  today: { label: 'Today' },
  week: { label: 'This Week' },
  month: { label: 'This Month' },
  custom: { label: 'Custom' },
};

export default function DateRangeFilter({
  preset,
  customRange,
  onChange,
}: DateRangeFilterProps) {
  const [showCustom, setShowCustom] = useState(preset === 'custom');
  const [startDate, setStartDate] = useState(
    customRange?.start ? customRange.start.toISOString().split('T')[0] : ''
  );
  const [endDate, setEndDate] = useState(
    customRange?.end ? customRange.end.toISOString().split('T')[0] : ''
  );

  const handlePresetClick = (newPreset: DateRangePreset) => {
    if (newPreset === 'custom') {
      setShowCustom(true);
      onChange('custom', customRange);
    } else {
      setShowCustom(false);
      onChange(newPreset);
    }
  };

  const handleCustomApply = () => {
    const range: DateRange = {
      start: startDate ? new Date(startDate) : null,
      end: endDate ? new Date(endDate) : null,
    };
    onChange('custom', range);
  };

  return (
    <div className={styles.container}>
      <div className={styles.presets}>
        {(Object.keys(presetConfig) as DateRangePreset[]).map((p) => (
          <button
            key={p}
            type="button"
            className={`${styles.preset} ${preset === p ? styles.selected : ''}`}
            onClick={() => handlePresetClick(p)}
          >
            {presetConfig[p].label}
          </button>
        ))}
      </div>

      {showCustom && (
        <div className={styles.customRange}>
          <div className={styles.dateField}>
            <label htmlFor="startDate" className={styles.dateLabel}>From</label>
            <input
              type="date"
              id="startDate"
              className={styles.dateInput}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div className={styles.dateField}>
            <label htmlFor="endDate" className={styles.dateLabel}>To</label>
            <input
              type="date"
              id="endDate"
              className={styles.dateInput}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <button
            type="button"
            className={styles.applyButton}
            onClick={handleCustomApply}
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}
