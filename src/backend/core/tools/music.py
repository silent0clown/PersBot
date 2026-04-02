import os
import logging
import subprocess
import platform
from typing import Dict, Any, Optional

from .base import BaseTool
from .types import ToolResult, ValidationResult, ToolErrorCode

logger = logging.getLogger(__name__)


class MusicPlayerTool(BaseTool):
    """音乐播放工具"""

    def __init__(self):
        self._player = None
        self._current_file = None
        self._detect_player()

    def _detect_player(self):
        """检测系统可用的播放器"""
        system = platform.system()
        
        if system == "Linux":
            # 优先检测 mpv, 然后 vlc, paplay
            for player in ["mpv", "vlc", "paplay", "play"]:
                if self._check_player_exists(player):
                    self._player = player
                    break
        elif system == "Windows":
            self._player = "wmplayer"  # Windows Media Player
        elif system == "Darwin":
            self._player = "afplay"  # macOS 内置

    def _check_player_exists(self, player: str) -> bool:
        """检查播放器是否存在"""
        try:
            subprocess.run(
                ["which", player],
                capture_output=True,
                timeout=5
            )
            return True
        except:
            return False

    @property
    def name(self) -> str:
        return "play_music"

    @property
    def description(self) -> str:
        return "播放指定路径的音乐文件，或控制音乐播放(暂停/停止/下一首)。支持 mp3, wav, flac, ogg 等格式。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作: play(播放), pause(暂停), stop(停止), next(下一首)",
                    "default": "play"
                },
                "path": {
                    "type": "string",
                    "description": "音乐文件路径 (play 必需)"
                },
                "volume": {
                    "type": "integer",
                    "description": "音量 0-100",
                    "default": 80
                }
            },
            "required": ["action"]
        }

    @property
    def is_read_only(self) -> bool:
        return True  # 播放音乐不修改文件

    @property
    def is_concurrency_safe(self) -> bool:
        return True

    def validate_input(self, **kwargs) -> ValidationResult:
        action = kwargs.get("action", "play")
        
        if action == "play":
            path = kwargs.get("path", "")
            if not path:
                return ValidationResult.fail("播放音乐需要指定 path 参数")
            
            # 检查文件是否存在
            expanded_path = os.path.expanduser(path)
            if not os.path.exists(expanded_path):
                return ValidationResult.fail(f"音乐文件不存在: {path}")
        
        return ValidationResult.ok()

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "play")
        path = kwargs.get("path", "")
        volume = kwargs.get("volume", 80)

        try:
            if action == "play":
                return self._play(path, volume)
            elif action == "pause":
                return self._pause()
            elif action == "stop":
                return self._stop()
            elif action == "next":
                return self._next()
            else:
                return ToolResult.error(
                    f"不支持的操作: {action}",
                    ToolErrorCode.EXECUTION_ERROR
                )

        except Exception as e:
            logger.error(f"Music player error: {e}")
            return ToolResult.error(
                f"音乐播放失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )

    def _play(self, path: str, volume: int) -> ToolResult:
        """播放音乐"""
        expanded_path = os.path.expanduser(path)
        
        if not self._player:
            return ToolResult.error(
                "未找到可用的音乐播放器",
                ToolErrorCode.EXECUTION_ERROR
            )

        # 构建命令
        cmd = self._build_play_command(expanded_path, volume)
        
        # 后台播放
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        self._current_file = expanded_path
        return ToolResult.success(f"正在播放: {path}")

    def _pause(self) -> ToolResult:
        """暂停播放"""
        if platform.system() == "Linux" and self._player == "mpv":
            subprocess.run(["playerctl", "--player=mpv", "pause"], capture_output=True)
        return ToolResult.success("已暂停")

    def _stop(self) -> ToolResult:
        """停止播放"""
        if platform.system() == "Linux" and self._player == "mpv":
            subprocess.run(["playerctl", "--player=mpv", "stop"], capture_output=True)
        self._current_file = None
        return ToolResult.success("已停止")

    def _next(self) -> ToolResult:
        """下一首"""
        if platform.system() == "Linux" and self._player == "mpv":
            subprocess.run(["playerctl", "--player=mpv", "next"], capture_output=True)
            return ToolResult.success("已切换到下一首")
        return ToolResult.error("当前播放器不支持此操作", ToolErrorCode.EXECUTION_ERROR)

    def _build_play_command(self, path: str, volume: int) -> str:
        """构建播放命令"""
        if platform.system() == "Linux":
            if self._player == "mpv":
                return f"mpv --volume={volume} '{path}' &"
            elif self._player == "vlc":
                return f"vlc --play-and-pause --volume={volume} '{path}' &"
            elif self._player == "play":
                return f"play -v {volume/100} '{path}' &"
            else:
                return f"paplay -v {volume/100} '{path}' &"
        elif platform.system() == "Windows":
            return f'start "" "{path}"'
        elif platform.system() == "Darwin":
            return f"afplay -v {volume/100} '{path}' &"
        
        return f"echo 'Unsupported platform: {platform.system()}'"


class SearchMusicTool(BaseTool):
    """搜索音乐工具 (本地)"""

    @property
    def name(self) -> str:
        return "search_music"

    @property
    def description(self) -> str:
        return "在指定目录中搜索音乐文件。支持 mp3, wav, flac, ogg, m4a 等格式。"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "搜索目录",
                    "default": "~/Music"
                },
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词 (文件名匹配)",
                    "default": ""
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制",
                    "default": 20
                }
            },
            "required": []
        }

    @property
    def is_read_only(self) -> bool:
        return True

    @property
    def is_concurrency_safe(self) -> bool:
        return True

    def execute(self, **kwargs) -> ToolResult:
        search_path = kwargs.get("path", "~/Music")
        keyword = kwargs.get("keyword", "")
        limit = kwargs.get("limit", 20)

        music_extensions = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"]

        try:
            expanded_path = os.path.expanduser(search_path)
            
            if not os.path.exists(expanded_path):
                return ToolResult.error(
                    f"搜索目录不存在: {search_path}",
                    ToolErrorCode.EXECUTION_ERROR
                )

            results = []
            for root, dirs, files in os.walk(expanded_path):
                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in music_extensions:
                        if keyword and keyword.lower() not in filename.lower():
                            continue
                        
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, expanded_path)
                        
                        # 获取文件大小
                        size = os.path.getsize(full_path)
                        size_mb = size / (1024 * 1024)
                        
                        results.append({
                            "name": filename,
                            "path": rel_path,
                            "size": f"{size_mb:.1f}MB"
                        })
                        
                        if len(results) >= limit:
                            break
                
                if len(results) >= limit:
                    break

            if not results:
                return ToolResult.success("未找到音乐文件")

            # 格式化输出
            output = f"找到 {len(results)} 个音乐文件:\n\n"
            for i, r in enumerate(results, 1):
                output += f"{i}. {r['name']}\n   路径: {r['path']}\n   大小: {r['size']}\n\n"

            return ToolResult.success(output.strip())

        except Exception as e:
            logger.error(f"Search music error: {e}")
            return ToolResult.error(
                f"搜索失败: {str(e)}",
                ToolErrorCode.EXECUTION_ERROR
            )