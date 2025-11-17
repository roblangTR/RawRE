import React, { useState } from 'react';
import { Film } from 'lucide-react';
import UploadPanel from './components/UploadPanel';
import CompilationPanel from './components/CompilationPanel';
import ShotLibrary from './components/ShotLibrary';
import useStore from './store/useStore';

function App() {
  const [storySlug, setStorySlug] = useState('');
  const [brief, setBrief] = useState('');
  const [targetDuration, setTargetDuration] = useState(90);
  const [maxIterations, setMaxIterations] = useState(3);
  
  const shots = useStore((state) => state.shots);
  const storeStorySlug = useStore((state) => state.storySlug);

  // Use store story slug if available
  const activeStorySlug = storeStorySlug || storySlug;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center gap-3">
          <Film size={32} className="text-blue-500" />
          <div>
            <h1 className="text-2xl font-bold">RAWRE Video Editor</h1>
            <p className="text-sm text-gray-400">AI-Powered News Editing Assistant</p>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex h-[calc(100vh-73px)]">
        {/* Left Sidebar - Shot Library */}
        <div className="w-80 border-r border-gray-700 bg-gray-800 overflow-hidden">
          <ShotLibrary />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Upload Panel */}
            <UploadPanel />

            {/* Configuration Inputs */}
            {shots.length > 0 && (
              <div className="panel space-y-4">
                <h2 className="text-xl font-bold">Edit Configuration</h2>

                {/* Story Slug */}
                <div>
                  <label className="block text-sm font-medium mb-2">Story Slug</label>
                  <input
                    type="text"
                    value={activeStorySlug}
                    onChange={(e) => setStorySlug(e.target.value)}
                    placeholder="e.g., climate-protest-2024"
                    className="input-field w-full"
                    disabled={!!storeStorySlug}
                  />
                </div>

                {/* Editorial Brief */}
                <div>
                  <label className="block text-sm font-medium mb-2">Editorial Brief *</label>
                  <textarea
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    placeholder="Describe the story and what you want the edit to focus on..."
                    rows={4}
                    className="input-field w-full resize-none"
                  />
                </div>

                {/* Target Duration */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Target Duration: {targetDuration}s
                  </label>
                  <input
                    type="range"
                    min="30"
                    max="300"
                    step="10"
                    value={targetDuration}
                    onChange={(e) => setTargetDuration(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>30s</span>
                    <span>300s</span>
                  </div>
                </div>

                {/* Max Iterations */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Max Iterations: {maxIterations}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={maxIterations}
                    onChange={(e) => setMaxIterations(Number(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>1</span>
                    <span>5</span>
                  </div>
                </div>
              </div>
            )}

            {/* Compilation Panel */}
            {shots.length > 0 && (
              <CompilationPanel
                storySlug={activeStorySlug}
                brief={brief}
                targetDuration={targetDuration}
                maxIterations={maxIterations}
              />
            )}

            {/* Placeholder for future components */}
            {shots.length === 0 && (
              <div className="panel text-center py-12">
                <Film size={48} className="mx-auto mb-4 text-gray-600" />
                <h3 className="text-lg font-medium mb-2">No Videos Uploaded</h3>
                <p className="text-gray-400">
                  Upload video files to get started with AI-powered editing
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
