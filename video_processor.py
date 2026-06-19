import os
import subprocess
from pathlib import Path
from config import PICS_DIR, FFMPEG_CONFIG, VIDEO_FORMATS

class VideoProcessor:
    def __init__(self):
        self.pics_dir = PICS_DIR
        self._ensure_dir()
    
    def _ensure_dir(self):
        self.pics_dir.mkdir(parents=True, exist_ok=True)
    
    def is_valid_video_file(self, file_path):
        """检查文件是否为有效的视频文件"""
        if not os.path.exists(file_path):
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in VIDEO_FORMATS
    
    def extract_keyframes(self, video_path, output_pattern=None):
        """
        使用FFmpeg提取视频关键帧
        
        Args:
            video_path: 输入视频文件路径
            output_pattern: 输出图片命名模式，默认为配置中的值
        
        Returns:
            int: 提取的关键帧数量
        """
        if not self.is_valid_video_file(video_path):
            raise ValueError(f"无效的视频文件格式: {video_path}")
        
        output_pattern = output_pattern or FFMPEG_CONFIG["output_pattern"]
        output_path = self.pics_dir / output_pattern
        
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"select='gt(scene,{FFMPEG_CONFIG['scene_threshold']})'",
            "-vsync", FFMPEG_CONFIG["vsync_mode"],
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            print(f"FFmpeg输出: {result.stdout}")
            if result.stderr:
                print(f"FFmpeg警告: {result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg执行失败: {e.stderr}")
            raise
        
        extracted_frames = list(self.pics_dir.glob("frame_*.jpg"))
        return len(extracted_frames)
    
    def get_extracted_frames(self):
        """获取已提取的所有关键帧文件列表"""
        frames = sorted(self.pics_dir.glob("frame_*.jpg"))
        return [str(f.name) for f in frames]
    
    def clear_frames(self):
        """清空pics目录下的所有图片文件"""
        for file in self.pics_dir.glob("*"):
            if file.is_file() and file.suffix.lower() in (".jpg", ".png", ".jpeg"):
                os.remove(file)
        print("已清空pics目录")