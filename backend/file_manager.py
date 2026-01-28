"""
File Manager Module
Organizes output files and creates info files for each clip
"""

from pathlib import Path
import shutil
from datetime import datetime
from typing import List, Dict
import re
import json


class FileManager:
    def __init__(self, base_output_dir: str = "./ToUpload"):
        """
        Initialize file manager

        Args:
            base_output_dir: Base directory for all output
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize string for use in filename

        Args:
            name: String to sanitize

        Returns:
            Safe filename string
        """
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Limit length
        name = name[:100]
        return name

    def create_project_folder(self, video_title: str) -> Path:
        """
        Create project folder for video

        Args:
            video_title: Video title

        Returns:
            Path to created folder
        """
        # Create folder name with title and date
        safe_title = self.sanitize_filename(video_title)
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{safe_title}_{date_str}"

        # Create folder
        project_folder = self.base_output_dir / folder_name

        # If folder exists, add number suffix
        counter = 1
        while project_folder.exists():
            project_folder = self.base_output_dir / f"{folder_name}_{counter}"
            counter += 1

        project_folder.mkdir(parents=True, exist_ok=True)

        # Create subfolders
        (project_folder / "original").mkdir(exist_ok=True)
        (project_folder / "reels").mkdir(exist_ok=True)

        return project_folder

    def create_info_file(
        self,
        clip_path: str,
        video_info: Dict,
        clip_info: Dict,
        caption_text: str
    ) -> str:
        """
        Create _info.json file for a clip

        Args:
            clip_path: Path to clip file
            video_info: Video metadata (title, channel, description, url)
            clip_info: Clip metadata (start, end, clip_number)
            caption_text: Full caption text

        Returns:
            Path to created info file
        """
        clip_path = Path(clip_path)
        info_path = clip_path.parent / f"{clip_path.stem}_info.json"

        # Format timestamp
        start_time = self._format_timestamp(clip_info['start_time'])
        end_time = self._format_timestamp(clip_info['end_time'])
        duration = clip_info['duration']

        # Determine format type
        format_type = "Reels (9:16)" if "reels" in str(clip_path) else "Original (16:9)"

        # Get AI-generated clip metadata
        clip_title = clip_info.get('title', 'Interesting Clip')
        clip_reason = clip_info.get('reason', '')
        clip_keywords = clip_info.get('keywords', [])

        # Create structured JSON data
        info_data = {
            "clip": {
                "title": clip_title,
                "description": clip_reason,
                "keywords": clip_keywords,
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration,
                "format": format_type
            },
            "video": {
                "title": video_info['title'],
                "channel": video_info['channel'],
                "description": video_info.get('description', 'N/A')[:500],
                "url": video_info['url']
            },
            "transcript": caption_text
        }

        # Write to JSON file
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, indent=2, ensure_ascii=False)

        return str(info_path)

    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds to MM:SS or H:MM:SS

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

    def organize_clips(
        self,
        clips: List[Dict],
        project_folder: Path,
        video_info: Dict,
        format_type: str = "original"
    ) -> List[Dict]:
        """
        Organize clips into project folder structure

        Args:
            clips: List of clip dictionaries with paths
            project_folder: Project folder path
            video_info: Video metadata
            format_type: "original" or "reels"

        Returns:
            List of organized clips with new paths
        """
        format_folder = project_folder / format_type
        organized_clips = []

        for clip in clips:
            clip_number = clip.get('clip_number', 0)

            # Determine new filename
            new_filename = f"clip_{clip_number:03d}.mp4"
            new_path = format_folder / new_filename

            # Copy clip to new location
            shutil.copy2(clip['clip_path'], new_path)

            # Create info file (including AI-generated metadata)
            info_path = self.create_info_file(
                clip_path=str(new_path),
                video_info=video_info,
                clip_info={
                    'start_time': clip['start_time'],
                    'end_time': clip['end_time'],
                    'duration': clip['duration'],
                    'clip_number': clip_number,
                    'title': clip.get('title', 'Interesting Clip'),
                    'reason': clip.get('reason', ''),
                    'keywords': clip.get('keywords', [])
                },
                caption_text=clip.get('caption_text', clip.get('text', ''))
            )

            organized_clips.append({
                **clip,
                'final_path': str(new_path),
                'info_path': info_path,
                'format_type': format_type
            })

        return organized_clips

    def cleanup_temp_files(self, temp_files: List[str]):
        """
        Clean up temporary files

        Args:
            temp_files: List of file paths to delete
        """
        for file_path in temp_files:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

    def get_project_summary(self, project_folder: Path) -> Dict:
        """
        Get summary of project folder

        Args:
            project_folder: Path to project folder

        Returns:
            dict with summary info
        """
        original_folder = project_folder / "original"
        reels_folder = project_folder / "reels"

        original_clips = list(original_folder.glob("clip_*.mp4"))
        reels_clips = list(reels_folder.glob("clip_*.mp4"))

        return {
            'project_folder': str(project_folder),
            'original_count': len(original_clips),
            'reels_count': len(reels_clips),
            'total_clips': len(original_clips) + len(reels_clips),
            'original_clips': [str(p) for p in original_clips],
            'reels_clips': [str(p) for p in reels_clips]
        }
