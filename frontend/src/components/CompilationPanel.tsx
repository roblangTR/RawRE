import React, { useState, useEffect } from 'react';
import { Play, Loader2, CheckCircle, XCircle, Download } from 'lucide-react';
import useStore from '../store/useStore';
import { api } from '../api/client';

interface CompilationPanelProps {
  storySlug: string;
  brief: string;
  targetDuration: number;
  maxIterations: number;
}

const CompilationPanel: React.FC<CompilationPanelProps> = ({
  storySlug,
  brief,
  targetDuration,
  maxIterations,
}) => {
  const [minScore, setMinScore] = useState(7.0);
  
  const isCompiling = useStore((state) => state.isCompiling);
  const setIsCompiling = useStore((state) => state.setIsCompiling);
  const compilationJobId = useStore((state) => state.compilationJobId);
  const setCompilationJobId = useStore((state) => state.setCompilationJobId);
  const setCompilationStatus = useStore((state) => state.setCompilationStatus);
  const setCompilationResult = useStore((state) => state.setCompilationResult);
  const compilationStatus = useStore((state) => state.compilationStatus);
  const compilationResult = useStore((state) => state.compilationResult);

  // Poll for compilation status
  useEffect(() => {
    if (!compilationJobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await api.getCompilationStatus(compilationJobId);
        setCompilationStatus(status);

        // Check if complete or failed
        if (status.status === 'complete' || status.status === 'failed') {
          setIsCompiling(false);
          clearInterval(pollInterval);

          // Fetch result if complete
          if (status.status === 'complete') {
            try {
              const result = await api.getCompilationResult(compilationJobId);
              console.log('Compilation result:', result);
              if (result) {
                setCompilationResult(result);
              }
            } catch (error) {
              console.error('Failed to fetch compilation result:', error);
            }
          }
        }
      } catch (error) {
        console.error('Failed to poll compilation status:', error);
        // Don't stop polling on error, keep trying
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [compilationJobId, setCompilationStatus, setCompilationResult, setIsCompiling]);

  const handleStartCompilation = async () => {
    if (!storySlug || !brief) {
      alert('Please provide story slug and editorial brief');
      return;
    }

    setIsCompiling(true);

    try {
      const { job_id } = await api.startCompilation({
        story_slug: storySlug,
        brief,
        target_duration: targetDuration,
        max_iterations: maxIterations,
        min_verification_score: minScore,
      });

      setCompilationJobId(job_id);

      // Clear any previous status/result
      setCompilationStatus(null);
      setCompilationResult(null);
    } catch (error: any) {
      console.error('Failed to start compilation:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to start compilation. Please try again.';
      alert(errorMsg);
      setIsCompiling(false);
    }
  };

  const handleDownloadEDL = async () => {
    if (!compilationJobId) return;

    try {
      const blob = await api.downloadEDL(compilationJobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${storySlug}_edit.edl`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download EDL:', error);
      alert('Failed to download EDL. Please try again.');
    }
  };

  const canStart = storySlug && brief && !isCompiling;

  return (
    <div className="panel space-y-4">
      <h2 className="text-xl font-bold">Compilation Settings</h2>

      {/* Minimum Score */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Minimum Quality Score: {minScore.toFixed(1)}/10
        </label>
        <input
          type="range"
          min="5"
          max="9"
          step="0.5"
          value={minScore}
          onChange={(e) => setMinScore(Number(e.target.value))}
          className="w-full"
          disabled={isCompiling}
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>5.0</span>
          <span>9.0</span>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          The AI will iterate until this quality threshold is met
        </p>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStartCompilation}
        disabled={!canStart}
        className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isCompiling ? (
          <>
            <Loader2 className="animate-spin" size={18} />
            Compiling...
          </>
        ) : (
          <>
            <Play size={18} />
            Start Compilation
          </>
        )}
      </button>

      {/* Status Display */}
      {compilationStatus && (
        <div className="mt-4 p-4 bg-gray-700 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">Status</span>
            <span className="text-sm text-gray-400">
              Iteration {compilationStatus.current_iteration}/{compilationStatus.max_iterations}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-600 rounded-full h-2 mb-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${compilationStatus.progress}%` }}
            />
          </div>

          {/* Current Phase */}
          <div className="flex items-center gap-2 text-sm">
            {compilationStatus.status === 'complete' ? (
              <CheckCircle size={16} className="text-green-400" />
            ) : compilationStatus.status === 'failed' ? (
              <XCircle size={16} className="text-red-400" />
            ) : (
              <Loader2 size={16} className="animate-spin text-blue-400" />
            )}
            <span className="capitalize">{compilationStatus.status}</span>
            {compilationStatus.current_agent && (
              <span className="text-gray-400">
                • {compilationStatus.current_agent}
              </span>
            )}
          </div>

          {compilationStatus.message && (
            <p className="text-xs text-gray-400 mt-2">{compilationStatus.message}</p>
          )}
        </div>
      )}

      {/* Result Summary */}
      {compilationResult && (
        <div className="mt-4 p-4 bg-gray-700 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium">Result</span>
            {compilationResult.approved ? (
              <span className="flex items-center gap-1 text-green-400">
                <CheckCircle size={16} />
                Approved
              </span>
            ) : (
              <span className="flex items-center gap-1 text-yellow-400">
                <XCircle size={16} />
                Not Approved
              </span>
            )}
          </div>

          {compilationResult.final_verification ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Overall Score:</span>
                <span className="font-medium">
                  {(compilationResult.final_verification.overall_score || 0).toFixed(1)}/10
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Total Shots:</span>
                <span>{compilationResult.final_selections?.total_shots || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Duration:</span>
                <span>
                  {(compilationResult.final_selections?.total_duration || 0).toFixed(1)}s
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Iterations:</span>
                <span>{compilationResult.iterations?.length || 0}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Compilation complete. Generating EDL...</p>
          )}

          {/* Download Button */}
          {compilationResult?.approved && (
            <button
              onClick={handleDownloadEDL}
              className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
            >
              <Download size={18} />
              Download EDL
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default CompilationPanel;
