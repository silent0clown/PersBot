import logging
import subprocess
import re
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class AppController:
    def __init__(self):
        self.app_map: Dict[str, str] = {
            "微信": "WeChat",
            "浏览器": "chrome",
            "chrome": "chrome",
            "edge": "msedge",
            "notepad": "notepad",
            "记事本": "notepad",
            "文件管理器": "explorer",
            "资源管理器": "explorer",
            "计算器": "calc",
            "画图": "mspaint",
            "截图": "snippingtool",
            "命令提示符": "cmd",
            "终端": "wt",
            "vscode": "code",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "音乐": "wmplayer",
            "视频": "wmplayer",
            "设置": "ms-settings:",
            "控制面板": "control",
        }
    
    async def execute(self, command: str) -> str:
        command = command.lower().strip()
        
        if self._match_command(command, ["打开", "启动", "运行"]):
            app_name = self._extract_app_name(command, ["打开", "启动", "运行"])
            return await self._open_app(app_name)
        
        elif self._match_command(command, ["关闭", "退出"]):
            app_name = self._extract_app_name(command, ["关闭", "退出"])
            return await self._close_app(app_name)
        
        elif command in ["截图", "截屏", "屏幕截图"]:
            return await self._screenshot()
        
        elif "最小化" in command:
            return await self._minimize_window()
        
        elif "最大化" in command:
            return await self._maximize_window()
        
        elif "关闭窗口" in command:
            return await self._close_window()
        
        else:
            return f"不支持的命令: {command}"
    
    def _match_command(self, command: str, keywords: list) -> bool:
        return any(kw in command for kw in keywords)
    
    def _extract_app_name(self, command: str, prefixes: list) -> str:
        for prefix in prefixes:
            if prefix in command:
                app_name = command.replace(prefix, "").strip()
                return app_name
        return command
    
    async def _open_app(self, app_name: str) -> str:
        try:
            if app_name in self.app_map:
                exe_name = self.app_map[app_name]
                
                if exe_name.startswith("ms-"):
                    subprocess.Popen(["cmd", "/c", "start", "", exe_name])
                else:
                    subprocess.Popen(["cmd", "/c", "start", "", exe_name])
                
                logger.info(f"Opened app: {app_name}")
                return f"已打开 {app_name}"
            
            else:
                subprocess.Popen(["cmd", "/c", "start", "", app_name])
                return f"已尝试打开 {app_name}"
                
        except Exception as e:
            logger.error(f"Failed to open app: {e}")
            return f"打开失败: {str(e)}"
    
    async def _close_app(self, app_name: str) -> str:
        try:
            if app_name in self.app_map:
                exe_name = self.app_map[app_name]
                subprocess.run(["taskkill", "/F", "/IM", f"{exe_name}.exe"], check=False)
                return f"已关闭 {app_name}"
            return f"未找到应用: {app_name}"
        except Exception as e:
            return f"关闭失败: {str(e)}"
    
    async def _screenshot(self) -> str:
        try:
            import pyautogui
            import datetime
            
            screenshot = pyautogui.screenshot()
            filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot.save(filename)
            
            logger.info(f"Screenshot saved: {filename}")
            return f"截图已保存: {filename}"
        except Exception as e:
            return f"截图失败: {str(e)}"
    
    async def _minimize_window(self) -> str:
        try:
            import pyautogui
            pyautogui.hotkey('win', 'down')
            return "已最小化"
        except Exception as e:
            return f"操作失败: {str(e)}"
    
    async def _maximize_window(self) -> str:
        try:
            import pyautogui
            pyautogui.hotkey('win', 'up')
            return "已最大化"
        except Exception as e:
            return f"操作失败: {str(e)}"
    
    async def _close_window(self) -> str:
        try:
            import pyautogui
            pyautogui.hotkey('alt', 'f4')
            return "已关闭窗口"
        except Exception as e:
            return f"操作失败: {str(e)}"
