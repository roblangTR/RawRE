import React from 'react';
import { Clock, User, MessageSquare } from 'lucide-react';
import type { Shot } from '../types';
import useStore from '../store/useStore';

interface ShotThumbnailProps {
  shot: Shot;
  beatNumber?: number;
  onClick?: () => void;
}

const ShotThumbnail: React.FC<ShotThumbnailProps> = ({ shot, beatNumber, onClick }) => {
  const isShotSelected = useStore((state) => state.isShotSelected);
  const isSelected = isShotSelected(shot.id);
  
  const durationSeconds = (shot.duration / 1000).toFixed(1);
  
  const getShotTypeBadgeClass = (type?: string | null) => {
    switch (type) {
      case 'SOT':
        return 'badge-sot';
      case 'GV':
        return 'badge-gv';
      case 'CUTAWAY':
        return 'badge-cutaway';
      default:
        return 'bg-gray-700 text-gray-300';
    }
  };

  return (
    <div
      className={`shot-thumbnail ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      {/* Thumbnail image placeholder */}
      <div className="aspect-video bg-gray-700 flex items-center justify-center relative">
        {shot.thumbnailUrl ? (
          <img
            src={`http://localhost:8000${shot.thumbnailUrl}`}
            alt={`Shot ${shot.id}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-gray-500 text-sm">No thumbnail</div>
        )}
        
        {/* Duration overlay */}
        <div className="absolute bottom-1 right-1 bg-black bg-opacity-75 px-1.5 py-0.5 rounded text-xs flex items-center gap-1">
          <Clock size={12} />
          {durationSeconds}s
        </div>
        
        {/* Beat number badge (if selected) */}
        {isSelected && beatNumber !== undefined && (
          <div className="absolute top-1 left-1 bg-red-600 text-white font-bold px-2 py-1 rounded-full text-xs">
            B{beatNumber}
          </div>
        )}
      </div>
      
      {/* Metadata */}
      <div className="p-2 space-y-1">
        {/* Shot type and ID */}
        <div className="flex items-center justify-between">
          <span className={`badge ${getShotTypeBadgeClass(shot.shotType)}`}>
            {shot.shotType || 'UNKNOWN'}
          </span>
          <span className="text-xs text-gray-400">#{shot.id}</span>
        </div>
        
        {/* Timecode */}
        <div className="text-xs text-gray-400 font-mono">
          {shot.timecode.in} - {shot.timecode.out}
        </div>
        
        {/* Features */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          {shot.hasFace && (
            <div className="flex items-center gap-1">
              <User size={12} />
              <span>Face</span>
            </div>
          )}
          {shot.hasSpeech && (
            <div className="flex items-center gap-1">
              <MessageSquare size={12} />
              <span>Speech</span>
            </div>
          )}
        </div>
        
        {/* Transcript preview */}
        {shot.transcript && (
          <div className="text-xs text-gray-300 line-clamp-2 mt-1">
            {shot.transcript}
          </div>
        )}
        
        {/* Description preview */}
        {shot.description && !shot.transcript && (
          <div className="text-xs text-gray-300 line-clamp-2 mt-1">
            {shot.description}
          </div>
        )}
      </div>
    </div>
  );
};

export default ShotThumbnail;
