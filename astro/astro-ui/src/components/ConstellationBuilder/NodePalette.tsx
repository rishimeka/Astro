'use client';

import { useState } from 'react';
import {
  Search,
  Cog,
  GitBranch,
  CheckCircle,
  Combine,
  Play,
  FileText,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { NodePaletteProps, PaletteItem, StarType } from './types';
import { starTypeColors, starTypeLabels } from './nodes/nodeStyles';
import styles from './NodePalette.module.scss';

// Icon mapping for star types
const starTypeIcons: Record<StarType, typeof Cog> = {
  worker: Cog,
  planning: GitBranch,
  eval: CheckCircle,
  synthesis: Combine,
  execution: Play,
  docex: FileText,
};

interface GroupedStars {
  [key: string]: PaletteItem[];
}

export function NodePalette({ stars, onSearch }: NodePaletteProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Set<StarType>>(
    new Set(['worker', 'planning', 'eval', 'synthesis', 'execution', 'docex'])
  );

  // Filter stars by search query
  const filteredStars = stars.filter(
    (star) =>
      star.starName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      star.directiveName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group stars by type
  const groupedStars: GroupedStars = filteredStars.reduce((acc, star) => {
    if (!acc[star.starType]) {
      acc[star.starType] = [];
    }
    acc[star.starType].push(star);
    return acc;
  }, {} as GroupedStars);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    if (onSearch) {
      onSearch(value);
    }
  };

  const toggleGroup = (type: StarType) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(type)) {
      newExpanded.delete(type);
    } else {
      newExpanded.add(type);
    }
    setExpandedGroups(newExpanded);
  };

  const handleDragStart = (event: React.DragEvent, item: PaletteItem) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(item));
    event.dataTransfer.effectAllowed = 'move';
  };

  // Order of star types to display
  const starTypeOrder: StarType[] = [
    'worker',
    'planning',
    'eval',
    'synthesis',
    'execution',
    'docex',
  ];

  return (
    <div className={styles.palette}>
      <h3 className={styles.title}>Add Nodes</h3>

      <div className={styles.searchWrapper}>
        <Search size={16} className={styles.searchIcon} />
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search stars..."
          value={searchQuery}
          onChange={handleSearchChange}
        />
      </div>

      <div className={styles.groups}>
        {starTypeOrder.map((type) => {
          const items = groupedStars[type];
          if (!items || items.length === 0) return null;

          const Icon = starTypeIcons[type];
          const isExpanded = expandedGroups.has(type);
          const color = starTypeColors[type];

          return (
            <div key={type} className={styles.group}>
              <button
                className={styles.groupHeader}
                onClick={() => toggleGroup(type)}
              >
                {isExpanded ? (
                  <ChevronDown size={16} className={styles.chevron} />
                ) : (
                  <ChevronRight size={16} className={styles.chevron} />
                )}
                <span className={styles.groupLabel}>
                  {starTypeLabels[type]} Stars
                </span>
                <span className={styles.groupCount}>{items.length}</span>
              </button>

              {isExpanded && (
                <div className={styles.groupItems}>
                  {items.map((item) => (
                    <div
                      key={`${item.starId}-${item.directiveId}`}
                      className={styles.paletteItem}
                      draggable
                      onDragStart={(e) => handleDragStart(e, item)}
                    >
                      <div
                        className={styles.itemIcon}
                        style={{ backgroundColor: `${color}20` }}
                      >
                        <Icon size={14} color={color} />
                      </div>
                      <div className={styles.itemInfo}>
                        <span className={styles.itemName}>{item.starName}</span>
                        <span className={styles.itemDirective}>
                          {item.directiveName}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {Object.keys(groupedStars).length === 0 && (
          <div className={styles.emptyState}>
            {searchQuery
              ? 'No stars match your search'
              : 'No stars available'}
          </div>
        )}
      </div>
    </div>
  );
}
