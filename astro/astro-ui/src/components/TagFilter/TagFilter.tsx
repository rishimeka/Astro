'use client';

import styles from './TagFilter.module.scss';

export interface TagFilterProps {
  tags: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  showAll?: boolean;
}

export default function TagFilter({
  tags,
  selected,
  onChange,
  showAll = true,
}: TagFilterProps) {
  const handleTagClick = (tag: string) => {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag));
    } else {
      onChange([...selected, tag]);
    }
  };

  const handleAllClick = () => {
    onChange([]);
  };

  const isAllSelected = selected.length === 0;

  return (
    <div className={styles.container}>
      {showAll && (
        <button
          type="button"
          className={`${styles.tag} ${isAllSelected ? styles.selected : ''}`}
          onClick={handleAllClick}
        >
          All
        </button>
      )}
      {tags.map((tag) => (
        <button
          key={tag}
          type="button"
          className={`${styles.tag} ${selected.includes(tag) ? styles.selected : ''}`}
          onClick={() => handleTagClick(tag)}
        >
          {tag}
        </button>
      ))}
    </div>
  );
}
