import React, { useState, useCallback } from 'react';
import { Upload, X, FileVideo, Loader2 } from 'lucide-react';
import useStore from '../store/useStore';
import { api } from '../api/client';

const UploadPanel: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [storySlug, setStorySlug] = useState('');
  const [brief, setBrief] = useState('');
  const [targetDuration, setTargetDuration] = useState(90);
  const [maxIterations, setMaxIterations] = useState(3);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingStory, setIsLoadingStory] = useState(false);
  
  const uploadProgress = useStore((state) => state.uploadProgress);
  const setUploadProgress = useStore((state) => state.setUploadProgress);
  const setShots = useStore((state) => state.setShots);
  const setStoreStorySlug = useStore((state) => state.setStorySlug);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.type.startsWith('video/')
    );
    setFiles((prev) => [...prev, ...droppedFiles]);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...selectedFiles]);
    }
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0 || !storySlug) {
      alert('Please select files and provide a story slug');
      return;
    }

    console.log('Starting upload:', files.length, 'files for story:', storySlug);
    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Upload files
      console.log('Calling uploadVideos API...');
      const uploadResult = await api.uploadVideos(files, storySlug, (progress) => {
        console.log('Upload progress:', progress + '%');
        setUploadProgress(progress);
      });

      console.log('Upload complete! Response:', uploadResult);
      console.log('Job ID:', uploadResult.job_id);
      console.log('Story slug:', uploadResult.story_slug);
      
      // Poll for ingestion status
      let pollCount = 0;
      const pollInterval = setInterval(async () => {
        pollCount++;
        console.log(`[Poll ${pollCount}] Checking ingestion status for job: ${uploadResult.job_id}`);
        
        try {
          const statusResult = await api.getIngestionStatus(uploadResult.job_id);
          console.log(`[Poll ${pollCount}] Status response:`, statusResult);
          
          const job = statusResult.job;
          console.log(`[Poll ${pollCount}] Status: ${job.status}, Progress: ${job.progress}%, Shots: ${job.total_shots}`);
          
          setUploadProgress(job.progress);

          if (job.status === 'completed') {
            console.log('Ingestion completed! Fetching shots...');
            clearInterval(pollInterval);
            
            // Fetch shots after ingestion completes
            const shots = await api.getShots(storySlug);
            console.log('Fetched shots:', shots);
            setShots(shots);
            setStoreStorySlug(storySlug);

            // Clear files
            setFiles([]);
            setUploadProgress(0);
            setIsUploading(false);
            
            alert(`Videos processed successfully! ${job.total_shots} shots extracted.`);
          } else if (job.status === 'failed') {
            console.error('Ingestion failed!', job.errors);
            clearInterval(pollInterval);
            setIsUploading(false);
            alert('Ingestion failed: ' + (job.errors.join(', ') || 'Unknown error'));
          }
        } catch (pollError) {
          console.error(`[Poll ${pollCount}] Error checking status:`, pollError);
          // Don't stop polling on individual errors
        }
      }, 2000); // Poll every 2 seconds

      // Safety timeout after 10 minutes
      setTimeout(() => {
        console.warn('Polling timeout reached after 10 minutes');
        clearInterval(pollInterval);
        setIsUploading(false);
        alert('Processing timeout. Please check the backend logs.');
      }, 600000);

    } catch (error) {
      console.error('Upload failed with error:', error);
      if (error.response) {
        console.error('Error response:', error.response.data);
        console.error('Error status:', error.response.status);
      }
      alert('Upload failed. Please try again. Check console for details.');
      setIsUploading(false);
    }
  };

  const handleLoadStory = async () => {
    if (!storySlug) {
      alert('Please enter a story slug');
      return;
    }

    console.log('Loading story:', storySlug);
    setIsLoadingStory(true);

    try {
      const shots = await api.getShots(storySlug);
      console.log('Loaded shots:', shots);
      
      if (shots.length === 0) {
        alert(`No shots found for story "${storySlug}". Upload videos first.`);
      } else {
        setShots(shots);
        setStoreStorySlug(storySlug);
        alert(`Loaded ${shots.length} shots for story "${storySlug}"`);
      }
    } catch (error: any) {
      console.error('Failed to load story:', error);
      alert(`Failed to load story "${storySlug}". Check console for details.`);
    } finally {
      setIsLoadingStory(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="panel space-y-4">
      <h2 className="text-xl font-bold">Upload & Configure</h2>

      {/* Story Slug */}
      <div>
        <label className="block text-sm font-medium mb-2">Story Slug *</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={storySlug}
            onChange={(e) => setStorySlug(e.target.value)}
            placeholder="e.g., TEST"
            className="input-field flex-1"
            disabled={isUploading || isLoadingStory}
          />
          <button
            onClick={handleLoadStory}
            disabled={isLoadingStory || !storySlug || isUploading}
            className="btn-secondary px-4 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoadingStory ? (
              <>
                <Loader2 className="animate-spin inline mr-1" size={16} />
                Loading...
              </>
            ) : (
              'Load Story'
            )}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Enter a story slug and click "Load Story" to view existing shots
        </p>
      </div>

      {/* File Upload */}
      <div>
        <label className="block text-sm font-medium mb-2">Video Files *</label>
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-blue-500 transition-colors cursor-pointer"
        >
          <Upload className="mx-auto mb-2 text-gray-400" size={32} />
          <p className="text-gray-400 mb-2">Drag and drop video files here</p>
          <p className="text-sm text-gray-500 mb-4">or</p>
          <label className="btn-secondary cursor-pointer inline-block">
            Browse Files
            <input
              type="file"
              multiple
              accept="video/*"
              onChange={handleFileSelect}
              className="hidden"
              disabled={isUploading}
            />
          </label>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between bg-gray-700 rounded p-3"
              >
                <div className="flex items-center gap-3">
                  <FileVideo size={20} className="text-blue-400" />
                  <div>
                    <div className="text-sm font-medium">{file.name}</div>
                    <div className="text-xs text-gray-400">{formatFileSize(file.size)}</div>
                  </div>
                </div>
                {!isUploading && (
                  <button
                    onClick={() => removeFile(index)}
                    className="text-gray-400 hover:text-red-400 transition-colors"
                  >
                    <X size={18} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Upload Progress */}
        {isUploading && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">
                {uploadProgress < 100 ? 'Uploading...' : 'Processing videos...'}
              </span>
              <span className="text-sm font-medium">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-2">
              This may take several minutes depending on video length...
            </p>
          </div>
        )}
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
          disabled={isUploading}
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
          disabled={isUploading}
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
          disabled={isUploading}
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>1</span>
          <span>5</span>
        </div>
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={isUploading || files.length === 0 || !storySlug}
        className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isUploading ? (
          <>
            <Loader2 className="animate-spin" size={18} />
            Processing...
          </>
        ) : (
          <>
            <Upload size={18} />
            Upload & Process Videos
          </>
        )}
      </button>
    </div>
  );
};

export default UploadPanel;
