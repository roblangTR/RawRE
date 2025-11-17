import React, { useState, useMemo } from 'react';
import { Search, Filter, SortAsc } from 'lucide-react';
import ShotThumbnail from './ShotThumbnail';
import useStore from '../store/useStore';
import type { Shot } from '../types';

const ShotLibrary: React.FC = () => {
  const shots = useStore((state) => state.shots);
  const compilationResult = useStore((state) => state.compilationResult);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [filterShotType, setFilterShotType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'time' | 'duration' | 'relevance'>('time');
  
  // Get beat number for each selected shot
  const shotBeatMap = useMemo(() => {
    const map = new Map<number, number>();
    if (compilationResult?.final_selections) {
      compilationResult.final_selections.selections.forEach((sel) => {
        map.set(sel.shot_id, sel.beat_number);
      });
    }
    return map;
  }, [compilationResult]);
  
  // Filter and sort shots
  const filteredShots = useMemo(() => {
    let filtered = [...shots];
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (shot) =>
          shot.asr_text?.toLowerCase().includes(query) ||
          shot.asr_summary?.toLowerCase().includes(query) ||
          shot.gemini_description?.toLowerCase().includes(query) ||
          shot.shot_id.toString().includes(query)
      );
    }
    
    // Shot type filter
    if (filterShotType !== 'all') {
      filtered = filtered.filter((shot) => shot.shot_type === filterShotType);
    }
    
    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'time':
          return a.capture_ts - b.capture_ts;
        case 'duration':
          return b.duration_ms - a.duration_ms;
        case 'relevance':
          return (b.relevance_score || 0) - (a.relevance_score || 0);
        default:
          return 0;
      }
    });
    
    return filtered;
  }, [shots, searchQuery, filterShotType, sortBy]);
  
  const shotTypeCounts = useMemo(() => {
    const counts: Record<string, number> = { all: shots.length };
    shots.forEach((shot) => {
      const type = shot.shot_type || 'UNKNOWN';
      counts[type] = (counts[type] || 0) + 1;
    });
    return counts;
  }, [shots]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-xl font-bold mb-4">Shot Library</h2>
        
        {/* Search */}
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search shots..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field w-full pl-10"
          />
        </div>
        
        {/* Filters */}
        <div className="flex gap-2 mb-3">
          <div className="flex-1">
            <label className="text-xs text-gray-400 mb-1 block">
              <Filter size={12} className="inline mr-1" />
              Shot Type
            </label>
            <select
              value={filterShotType}
              onChange={(e) => setFilterShotType(e.target.value)}
              className="input-field w-full text-sm"
            >
              <option value="all">All ({shotTypeCounts.all})</option>
              {shotTypeCounts.SOT && <option value="SOT">SOT ({shotTypeCounts.SOT})</option>}
              {shotTypeCounts.GV && <option value="GV">GV ({shotTypeCounts.GV})</option>}
              {shotTypeCounts.CUTAWAY && <option value="CUTAWAY">Cutaway ({shotTypeCounts.CUTAWAY})</option>}
            </select>
          </div>
          
          <div className="flex-1">
            <label className="text-xs text-gray-400 mb-1 block">
              <SortAsc size={12} className="inline mr-1" />
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="input-field w-full text-sm"
            >
              <option value="time">Capture Time</option>
              <option value="duration">Duration</option>
              <option value="relevance">Relevance</option>
            </select>
          </div>
        </div>
        
        {/* Stats */}
        <div className="text-sm text-gray-400">
          Showing {filteredShots.length} of {shots.length} shots
        </div>
      </div>
      
      {/* Shot Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredShots.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            {shots.length === 0 ? 'No shots available. Upload videos to get started.' : 'No shots match your filters.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filteredShots.map((shot) => (
              <ShotThumbnail
                key={shot.shot_id}
                shot={shot}
                beatNumber={shotBeatMap.get(shot.shot_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ShotLibrary;
