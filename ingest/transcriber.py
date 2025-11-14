"""Audio transcription using MLX-Whisper."""

import mlx_whisper
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import tempfile


class Transcriber:
    """Handles audio transcription with word-level timestamps."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config['audio']['whisper_model']
        self.language = config['audio']['language']
        self.word_timestamps = config['audio']['word_timestamps']
        self.model = None
    
    def _load_model(self):
        """Lazy load Whisper model."""
        if self.model is None:
            print(f"Loading Whisper model: {self.model_name}")
            # MLX Whisper will download model if needed
            self.model = self.model_name
    
    def extract_audio(self, video_path: Path) -> Path:
        """Extract audio from video to temporary WAV file."""
        temp_audio = Path(tempfile.mktemp(suffix='.wav'))
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',
            '-ar', '16000',  # 16kHz sample rate for Whisper
            '-ac', '1',  # Mono
            '-y',
            str(temp_audio)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return temp_audio
    
    def transcribe_segment(self, audio_path: Path, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        Transcribe a specific segment of audio.
        
        Returns:
            Dictionary with 'text', 'words' (if word_timestamps enabled)
        """
        self._load_model()
        
        # Extract segment
        temp_segment = Path(tempfile.mktemp(suffix='.wav'))
        
        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-ss', str(start_time),
            '-to', str(end_time),
            '-y',
            str(temp_segment)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        # Transcribe using MLX Whisper
        try:
            result = mlx_whisper.transcribe(
                str(temp_segment),
                path_or_hf_repo=self.model_name,
                language=self.language,
                word_timestamps=self.word_timestamps
            )
            
            # Clean up
            temp_segment.unlink()
            
            # Extract text and words
            text = result.get('text', '').strip()
            
            words = []
            if self.word_timestamps and 'segments' in result:
                for segment in result['segments']:
                    if 'words' in segment:
                        for word_info in segment['words']:
                            words.append({
                                'word': word_info.get('word', '').strip(),
                                'start': word_info.get('start', 0.0) + start_time,
                                'end': word_info.get('end', 0.0) + start_time,
                                'probability': word_info.get('probability', 1.0)
                            })
            
            return {
                'text': text,
                'words': words,
                'language': result.get('language', self.language)
            }
        
        except Exception as e:
            print(f"Transcription error: {e}")
            temp_segment.unlink(missing_ok=True)
            return {
                'text': '',
                'words': [],
                'language': self.language
            }
    
    def transcribe_video(self, video_path: Path, shots: List[Any]) -> List[Dict[str, Any]]:
        """
        Transcribe all shots in a video.
        
        Args:
            video_path: Path to video file
            shots: List of Shot objects with start_time and end_time
        
        Returns:
            List of transcription results, one per shot
        """
        print(f"Transcribing audio from {video_path.name}...")
        
        # Extract full audio once
        audio_path = self.extract_audio(video_path)
        
        transcriptions = []
        
        for i, shot in enumerate(shots):
            # Transcribe shot segment
            result = self.transcribe_segment(audio_path, shot.start_time, shot.end_time)
            transcriptions.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"  Transcribed {i + 1}/{len(shots)} shots")
        
        # Clean up audio file
        audio_path.unlink()
        
        print(f"✓ Transcribed {len(shots)} shots")
        
        return transcriptions
    
    def summarize_transcript(self, text: str, max_length: int = 200) -> str:
        """
        Create a brief summary of transcript.
        
        For prototype, just truncate. Could be enhanced with LLM summarization.
        """
        if len(text) <= max_length:
            return text
        
        # Truncate at word boundary
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + '...'
    
    def detect_speech_duration(self, words: List[Dict[str, Any]]) -> float:
        """Calculate total duration of speech in a segment."""
        if not words:
            return 0.0
        
        # Sum up word durations
        total_duration = 0.0
        for word in words:
            duration = word['end'] - word['start']
            total_duration += duration
        
        return total_duration
