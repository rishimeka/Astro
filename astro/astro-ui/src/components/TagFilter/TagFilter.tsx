'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, X, Check, Search } from 'lucide-react';
import styles from './TagFilter.module.scss';

export interface TagFilterProps {
  tags: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  showAll?: boolean;
  placeholder?: string;
}

export default function TagFilter({
  tags,
  selected,
  onChange,
  showAll = true,
  placeholder = 'Filter by tags...',
}: TagFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleTagToggle = (tag: string) => {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag));
    } else {
      onChange([...selected, tag]);
    }
  };

  const handleRemoveTag = (tag: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(selected.filter((t) => t !== tag));
  };

  const handleClearAll = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange([]);
  };

  const filteredTags = tags.filter((tag) =>
    tag.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.dropdownWrapper}>
        <button
          type="button"
          className={styles.trigger}
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span className={styles.triggerText}>
            {selected.length === 0 ? placeholder : `${selected.length} tag${selected.length > 1 ? 's' : ''} selected`}
          </span>
          <ChevronDown size={16} className={`${styles.chevron} ${isOpen ? styles.open : ''}`} />
        </button>

        {isOpen && (
          <div className={styles.dropdown}>
            <div className={styles.searchWrapper}>
              <Search size={14} className={styles.searchIcon} />
              <input
                ref={inputRef}
                type="text"
                className={styles.searchInput}
                placeholder="Search tags..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <div className={styles.optionsList}>
              {showAll && (
                <button
                  type="button"
                  className={`${styles.option} ${selected.length === 0 ? styles.selected : ''}`}
                  onClick={() => onChange([])}
                >
                  <span className={styles.optionLabel}>All</span>
                  {selected.length === 0 && <Check size={14} className={styles.checkIcon} />}
                </button>
              )}

              {filteredTags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  className={`${styles.option} ${selected.includes(tag) ? styles.selected : ''}`}
                  onClick={() => handleTagToggle(tag)}
                >
                  <span className={styles.optionLabel}>{tag}</span>
                  {selected.includes(tag) && <Check size={14} className={styles.checkIcon} />}
                </button>
              ))}

              {filteredTags.length === 0 && (
                <div className={styles.noResults}>No tags found</div>
              )}
            </div>
          </div>
        )}
      </div>

      {selected.length > 0 && (
        <div className={styles.selectedTags}>
          {selected.map((tag) => (
            <span key={tag} className={styles.selectedTag}>
              {tag}
              <button
                type="button"
                className={styles.removeTag}
                onClick={(e) => handleRemoveTag(tag, e)}
                aria-label={`Remove ${tag}`}
              >
                <X size={12} />
              </button>
            </span>
          ))}
          <button
            type="button"
            className={styles.clearAll}
            onClick={handleClearAll}
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
