'use client';

import { useState, useRef, useEffect, KeyboardEvent, ChangeEvent } from 'react';
import { useProbes } from '@/hooks/useProbes';
import { useDirectives } from '@/hooks/useDirectives';
import styles from './ContentEditor.module.scss';

export interface ContentEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  error?: boolean;
}

type AutocompleteMode = 'none' | 'type' | 'probe' | 'directive' | 'variable';

interface Suggestion {
  label: string;
  value: string;
  description?: string;
}

const TYPE_SUGGESTIONS: Suggestion[] = [
  { label: 'probe:', value: 'probe:', description: 'Reference a probe' },
  { label: 'directive:', value: 'directive:', description: 'Reference a directive' },
  { label: 'variable:', value: 'variable:', description: 'Define a variable' },
];

export default function ContentEditor({
  value,
  onChange,
  placeholder,
  className = '',
  error = false,
}: ContentEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const [mode, setMode] = useState<AutocompleteMode>('none');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [triggerPosition, setTriggerPosition] = useState<{ top: number; left: number } | null>(null);
  const [cursorPosition, setCursorPosition] = useState(0);

  const { probes, isLoading: probesLoading } = useProbes();
  const { directives, isLoading: directivesLoading } = useDirectives();

  // Get suggestions based on current mode
  const getSuggestions = (): Suggestion[] => {
    switch (mode) {
      case 'type':
        return TYPE_SUGGESTIONS.filter(s =>
          s.label.toLowerCase().includes(searchTerm.toLowerCase())
        );
      case 'probe':
        return probes
          .filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()))
          .map(p => ({
            label: p.name,
            value: p.name,
            description: p.description,
          }));
      case 'directive':
        return directives
          .filter(d => d.name.toLowerCase().includes(searchTerm.toLowerCase()))
          .map(d => ({
            label: d.name,
            value: d.id,
            description: d.description,
          }));
      default:
        return [];
    }
  };

  const suggestions = getSuggestions();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(event.target as Node)
      ) {
        setMode('none');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll selected item into view when navigating with keyboard
  useEffect(() => {
    if (listRef.current && mode !== 'none') {
      const selectedElement = listRef.current.children[selectedIndex] as HTMLElement;
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [selectedIndex, mode]);

  // Calculate dropdown position based on cursor
  const calculateDropdownPosition = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Create a hidden div to measure text position
    const mirror = document.createElement('div');
    const computed = window.getComputedStyle(textarea);

    // Copy relevant styles
    const stylesToCopy = [
      'font-family', 'font-size', 'font-weight', 'font-style',
      'letter-spacing', 'line-height', 'padding-top', 'padding-left',
      'padding-right', 'padding-bottom', 'border-width', 'box-sizing',
      'word-wrap', 'word-break', 'white-space'
    ];

    stylesToCopy.forEach(prop => {
      mirror.style.setProperty(prop, computed.getPropertyValue(prop));
    });

    mirror.style.position = 'absolute';
    mirror.style.visibility = 'hidden';
    mirror.style.whiteSpace = 'pre-wrap';
    mirror.style.width = `${textarea.clientWidth}px`;

    // Get text up to cursor
    const textBeforeCursor = value.substring(0, cursorPosition);
    mirror.textContent = textBeforeCursor;

    // Add a span at the cursor position to measure
    const cursorSpan = document.createElement('span');
    cursorSpan.textContent = '|';
    mirror.appendChild(cursorSpan);

    document.body.appendChild(mirror);

    const spanRect = cursorSpan.getBoundingClientRect();
    const mirrorRect = mirror.getBoundingClientRect();

    // Calculate position relative to textarea
    const top = spanRect.top - mirrorRect.top + parseInt(computed.paddingTop) - textarea.scrollTop;
    const left = spanRect.left - mirrorRect.left;

    document.body.removeChild(mirror);

    setTriggerPosition({
      top: Math.min(top + 20, textarea.clientHeight - 10), // Add line height offset, clamp to textarea
      left: Math.min(left, textarea.clientWidth - 200), // Clamp to prevent overflow
    });
  };

  // Handle text changes and detect autocomplete triggers
  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    const cursorPos = e.target.selectionStart;

    onChange(newValue);
    setCursorPosition(cursorPos);

    // Find the @ trigger before cursor
    const textBeforeCursor = newValue.substring(0, cursorPos);
    const atMatch = textBeforeCursor.match(/@([a-zA-Z]*)(?::([a-zA-Z0-9_-]*))?$/);

    if (atMatch) {
      const [, typePrefix, namePrefix] = atMatch;

      if (typePrefix === 'probe' && namePrefix !== undefined) {
        // User typed @probe: - show probe suggestions
        setMode('probe');
        setSearchTerm(namePrefix || '');
        setSelectedIndex(0);
        calculateDropdownPosition();
      } else if (typePrefix === 'directive' && namePrefix !== undefined) {
        // User typed @directive: - show directive suggestions
        setMode('directive');
        setSearchTerm(namePrefix || '');
        setSelectedIndex(0);
        calculateDropdownPosition();
      } else if (typePrefix === 'variable' && namePrefix !== undefined) {
        // User typed @variable: - just let them type (variables are user-defined)
        setMode('none');
      } else if (typePrefix !== undefined && namePrefix === undefined) {
        // User just typed @ or @p, @d, etc - show type suggestions
        setMode('type');
        setSearchTerm(typePrefix || '');
        setSelectedIndex(0);
        calculateDropdownPosition();
      } else {
        setMode('none');
      }
    } else {
      setMode('none');
    }
  };

  // Handle cursor position changes
  const handleSelect = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setCursorPosition(e.target.selectionStart);
  };

  // Insert selected suggestion
  const insertSuggestion = (suggestion: Suggestion) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const textBeforeCursor = value.substring(0, cursorPosition);
    const textAfterCursor = value.substring(cursorPosition);

    let newText: string;
    let newCursorPos: number;

    if (mode === 'type') {
      // Replace @prefix with @type:
      const atMatch = textBeforeCursor.match(/@([a-zA-Z]*)$/);
      if (atMatch) {
        const beforeAt = textBeforeCursor.substring(0, atMatch.index);
        newText = `${beforeAt}@${suggestion.value}${textAfterCursor}`;
        newCursorPos = beforeAt.length + 1 + suggestion.value.length;

        // If it's probe: or directive:, trigger the next autocomplete
        if (suggestion.value === 'probe:') {
          onChange(newText);
          setCursorPosition(newCursorPos);
          setMode('probe');
          setSearchTerm('');
          setSelectedIndex(0);
          calculateDropdownPosition();

          // Focus and set cursor after state update
          setTimeout(() => {
            textarea.focus();
            textarea.setSelectionRange(newCursorPos, newCursorPos);
          }, 0);
          return;
        } else if (suggestion.value === 'directive:') {
          onChange(newText);
          setCursorPosition(newCursorPos);
          setMode('directive');
          setSearchTerm('');
          setSelectedIndex(0);
          calculateDropdownPosition();

          setTimeout(() => {
            textarea.focus();
            textarea.setSelectionRange(newCursorPos, newCursorPos);
          }, 0);
          return;
        }
      } else {
        newText = value;
        newCursorPos = cursorPosition;
      }
    } else {
      // Replace @type:prefix with @type:value
      const atMatch = textBeforeCursor.match(/@(probe|directive):([a-zA-Z0-9_-]*)$/);
      if (atMatch) {
        const beforeAt = textBeforeCursor.substring(0, atMatch.index);
        const type = atMatch[1];
        newText = `${beforeAt}@${type}:${suggestion.value}${textAfterCursor}`;
        newCursorPos = beforeAt.length + 1 + type.length + 1 + suggestion.value.length;
      } else {
        newText = value;
        newCursorPos = cursorPosition;
      }
    }

    onChange(newText);
    setCursorPosition(newCursorPos);
    setMode('none');

    // Focus textarea and set cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  // Manually trigger autocomplete with Ctrl+Space or Option+Space (Mac)
  const triggerAutocomplete = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = value.substring(0, cursorPos);

    // Check if there's already an @ pattern before cursor
    const atMatch = textBeforeCursor.match(/@([a-zA-Z]*)(?::([a-zA-Z0-9_-]*))?$/);

    if (atMatch) {
      // Already have an @ pattern - just show the appropriate autocomplete
      const [, typePrefix, namePrefix] = atMatch;

      if (typePrefix === 'probe' && namePrefix !== undefined) {
        setMode('probe');
        setSearchTerm(namePrefix || '');
      } else if (typePrefix === 'directive' && namePrefix !== undefined) {
        setMode('directive');
        setSearchTerm(namePrefix || '');
      } else if (typePrefix === 'variable' && namePrefix !== undefined) {
        // Variables are user-defined, show type suggestions instead
        setMode('type');
        setSearchTerm(typePrefix || '');
      } else {
        setMode('type');
        setSearchTerm(typePrefix || '');
      }
    } else {
      // No @ pattern - insert @ and show type suggestions
      const newValue = value.substring(0, cursorPos) + '@' + value.substring(cursorPos);
      const newCursorPos = cursorPos + 1;

      onChange(newValue);
      setCursorPosition(newCursorPos);
      setMode('type');
      setSearchTerm('');

      // Set cursor position after state update
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(newCursorPos, newCursorPos);
      }, 0);
    }

    setSelectedIndex(0);
    calculateDropdownPosition();
  };

  // Handle keyboard navigation in dropdown
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Space or Option+Space (Alt+Space) to trigger autocomplete
    if (e.key === ' ' && (e.ctrlKey || e.altKey)) {
      e.preventDefault();
      triggerAutocomplete();
      return;
    }

    if (mode === 'none' || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % suggestions.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + suggestions.length) % suggestions.length);
        break;
      case 'Enter':
      case 'Tab':
        e.preventDefault();
        insertSuggestion(suggestions[selectedIndex]);
        break;
      case 'Escape':
        e.preventDefault();
        setMode('none');
        break;
    }
  };

  const isLoading = mode === 'probe' ? probesLoading : mode === 'directive' ? directivesLoading : false;

  return (
    <div className={styles.container}>
      <textarea
        ref={textareaRef}
        className={`textarea ${styles.textarea} ${error ? 'textarea-error' : ''} ${className}`}
        value={value}
        onChange={handleChange}
        onSelect={handleSelect}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
      />

      {mode !== 'none' && triggerPosition && (
        <div
          ref={dropdownRef}
          className={styles.dropdown}
          style={{
            top: `${triggerPosition.top}px`,
            left: `${triggerPosition.left}px`,
          }}
        >
          {isLoading ? (
            <div className={styles.loading}>Loading...</div>
          ) : suggestions.length > 0 ? (
            <ul ref={listRef} className={styles.suggestionsList}>
              {suggestions.map((suggestion, index) => (
                <li
                  key={suggestion.value}
                  className={`${styles.suggestion} ${index === selectedIndex ? styles.selected : ''}`}
                  onClick={() => insertSuggestion(suggestion)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <span className={styles.suggestionLabel}>{suggestion.label}</span>
                  {suggestion.description && (
                    <span className={styles.suggestionDescription}>{suggestion.description}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.noResults}>
              {mode === 'type' ? 'No matching types' : `No ${mode}s found`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
