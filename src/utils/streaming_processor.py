"""
流式处理器 - 实现实时反馈和进度更新

主要功能：
1. 流式API调用 - 支持实时接收生成内容
2. 进度跟踪 - 详细的进度反馈和状态更新
3. 实时预览 - 边生成边展示内容
4. 错误恢复 - 支持中断恢复和重试机制
"""

import asyncio
import json
import time
import threading
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import requests
from datetime import datetime
import websockets
import queue


class StreamingStatus(Enum):
    """流式处理状态"""
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamingEvent:
    """流式事件"""
    event_type: str  # progress, content, error, complete
    timestamp: datetime
    data: Dict[str, Any]
    stage: Optional[str] = None
    progress: Optional[float] = None


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self):
        self.stages = [
            "initialization",
            "creative_design", 
            "content_generation",
            "optimization"
        ]
        self.current_stage = 0
        self.stage_progress = 0.0
        self.overall_progress = 0.0
        self.start_time = None
        self.stage_start_time = None
        
    def start_tracking(self):
        """开始跟踪"""
        self.start_time = datetime.now()
        self.stage_start_time = datetime.now()
        self.current_stage = 0
        self.stage_progress = 0.0
        self.overall_progress = 0.0
    
    def update_stage_progress(self, progress: float):
        """更新当前阶段进度"""
        self.stage_progress = max(0.0, min(1.0, progress))
        
        # 计算总体进度
        stage_weight = 1.0 / len(self.stages)
        completed_stages_progress = self.current_stage * stage_weight
        current_stage_progress = self.stage_progress * stage_weight
        self.overall_progress = completed_stages_progress + current_stage_progress
    
    def next_stage(self):
        """进入下一阶段"""
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            self.stage_progress = 0.0
            self.stage_start_time = datetime.now()
    
    def get_current_stage_name(self) -> str:
        """获取当前阶段名称"""
        if self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return "completed"
    
    def get_estimated_time_remaining(self) -> Optional[float]:
        """估算剩余时间（秒）"""
        if not self.start_time or self.overall_progress <= 0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        estimated_total = elapsed / self.overall_progress
        return max(0, estimated_total - elapsed)
    
    def get_stage_info(self) -> Dict[str, Any]:
        """获取阶段信息"""
        return {
            'current_stage': self.get_current_stage_name(),
            'stage_index': self.current_stage,
            'total_stages': len(self.stages),
            'stage_progress': self.stage_progress,
            'overall_progress': self.overall_progress,
            'estimated_time_remaining': self.get_estimated_time_remaining()
        }


class StreamingProcessor:
    """流式处理器
    
    提供实时的故事生成反馈和进度更新
    """
    
    def __init__(self, 
                 progress_callback: Optional[Callable] = None,
                 content_callback: Optional[Callable] = None,
                 error_callback: Optional[Callable] = None):
        """初始化流式处理器
        
        Args:
            progress_callback: 进度更新回调 (stage, progress, message)
            content_callback: 内容更新回调 (content_chunk, is_complete)
            error_callback: 错误回调 (error_message, is_recoverable)
        """
        self.progress_callback = progress_callback
        self.content_callback = content_callback
        self.error_callback = error_callback
        
        self.status = StreamingStatus.IDLE
        self.progress_tracker = ProgressTracker()
        self.event_queue = queue.Queue()
        self.current_content = ""
        
        # 流式处理控制
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # WebSocket连接（如果需要）
        self.websocket_clients = set()
    
    def emit_progress(self, stage: str, progress: float, message: str):
        """发送进度更新"""
        event = StreamingEvent(
            event_type="progress",
            timestamp=datetime.now(),
            stage=stage,
            progress=progress,
            data={
                'stage': stage,
                'progress': progress,
                'message': message,
                'stage_info': self.progress_tracker.get_stage_info()
            }
        )
        
        self._emit_event(event)
        
        if self.progress_callback:
            self.progress_callback(stage, progress, message)
    
    def emit_content(self, content_chunk: str, is_complete: bool = False):
        """发送内容更新"""
        self.current_content += content_chunk
        
        event = StreamingEvent(
            event_type="content",
            timestamp=datetime.now(),
            data={
                'content_chunk': content_chunk,
                'total_content': self.current_content,
                'is_complete': is_complete,
                'content_length': len(self.current_content)
            }
        )
        
        self._emit_event(event)
        
        if self.content_callback:
            self.content_callback(content_chunk, is_complete)
    
    def emit_error(self, error_message: str, is_recoverable: bool = True):
        """发送错误信息"""
        event = StreamingEvent(
            event_type="error",
            timestamp=datetime.now(),
            data={
                'error_message': error_message,
                'is_recoverable': is_recoverable,
                'current_stage': self.progress_tracker.get_current_stage_name()
            }
        )
        
        self._emit_event(event)
        
        if self.error_callback:
            self.error_callback(error_message, is_recoverable)
    
    def _emit_event(self, event: StreamingEvent):
        """发送事件"""
        try:
            self.event_queue.put_nowait(event)
            
            # 如果有WebSocket客户端，广播事件
            if self.websocket_clients:
                asyncio.create_task(self._broadcast_to_websockets(event))
                
        except queue.Full:
            # 队列满了，移除最旧的事件
            try:
                self.event_queue.get_nowait()
                self.event_queue.put_nowait(event)
            except queue.Empty:
                pass
    
    async def _broadcast_to_websockets(self, event: StreamingEvent):
        """广播事件到WebSocket客户端"""
        if not self.websocket_clients:
            return
        
        message = json.dumps({
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat(),
            'stage': event.stage,
            'progress': event.progress,
            'data': event.data
        }, ensure_ascii=False)
        
        # 发送给所有连接的客户端
        disconnected_clients = set()
        for client in self.websocket_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                print(f"WebSocket发送失败: {e}")
                disconnected_clients.add(client)
        
        # 清理断开的连接
        self.websocket_clients -= disconnected_clients
    
    def start_streaming(self):
        """开始流式处理"""
        self.status = StreamingStatus.STREAMING
        self.progress_tracker.start_tracking()
        self._stop_event.clear()
        self._pause_event.clear()
        self.current_content = ""
        
        self.emit_progress("initialization", 0.0, "开始故事生成...")
    
    def pause_streaming(self):
        """暂停流式处理"""
        self.status = StreamingStatus.PAUSED
        self._pause_event.set()
        self.emit_progress(
            self.progress_tracker.get_current_stage_name(),
            self.progress_tracker.stage_progress,
            "处理已暂停"
        )
    
    def resume_streaming(self):
        """恢复流式处理"""
        self.status = StreamingStatus.STREAMING
        self._pause_event.clear()
        self.emit_progress(
            self.progress_tracker.get_current_stage_name(),
            self.progress_tracker.stage_progress,
            "处理已恢复"
        )
    
    def stop_streaming(self):
        """停止流式处理"""
        self.status = StreamingStatus.IDLE
        self._stop_event.set()
        self._pause_event.clear()
        self.emit_progress(
            self.progress_tracker.get_current_stage_name(),
            self.progress_tracker.stage_progress,
            "处理已停止"
        )
    
    def complete_streaming(self):
        """完成流式处理"""
        self.status = StreamingStatus.COMPLETED
        self.progress_tracker.overall_progress = 1.0
        
        event = StreamingEvent(
            event_type="complete",
            timestamp=datetime.now(),
            data={
                'total_content': self.current_content,
                'content_length': len(self.current_content),
                'total_time': (datetime.now() - self.progress_tracker.start_time).total_seconds()
            }
        )
        
        self._emit_event(event)
        self.emit_progress("completed", 1.0, "故事生成完成！")
    
    def wait_if_paused(self):
        """如果暂停则等待"""
        if self._pause_event.is_set():
            self._pause_event.wait()
    
    def should_stop(self) -> bool:
        """检查是否应该停止"""
        return self._stop_event.is_set()
    
    def simulate_streaming_api_call(self, 
                                   stage: str, 
                                   api_call_func: Callable,
                                   *args, **kwargs) -> Any:
        """模拟流式API调用
        
        将普通的API调用包装为流式处理，提供进度反馈
        """
        self.emit_progress(stage, 0.1, f"开始{stage}阶段...")
        
        # 检查暂停和停止
        self.wait_if_paused()
        if self.should_stop():
            return None
        
        try:
            # 模拟进度更新
            for i in range(3):
                if self.should_stop():
                    return None
                
                self.wait_if_paused()
                progress = 0.2 + (i * 0.2)
                self.emit_progress(stage, progress, f"{stage}处理中... ({i+1}/3)")
                time.sleep(0.5)  # 模拟处理时间
            
            # 执行实际的API调用
            self.emit_progress(stage, 0.8, f"正在调用API...")
            result = api_call_func(*args, **kwargs)
            
            if result:
                self.emit_progress(stage, 1.0, f"{stage}阶段完成")
                
                # 如果结果是文本内容，逐步发送
                if isinstance(result, str) and len(result) > 100:
                    self._stream_content(result)
                
                # 进入下一阶段
                self.progress_tracker.next_stage()
                
                return result
            else:
                self.emit_error(f"{stage}阶段失败：API返回空结果")
                return None
                
        except Exception as e:
            self.emit_error(f"{stage}阶段出错：{str(e)}")
            return None
    
    def _stream_content(self, content: str, chunk_size: int = 50):
        """流式发送内容"""
        words = content.split()
        
        for i in range(0, len(words), chunk_size):
            if self.should_stop():
                break
            
            self.wait_if_paused()
            
            chunk_words = words[i:i + chunk_size]
            chunk = " ".join(chunk_words)
            
            self.emit_content(chunk + " ")
            time.sleep(0.1)  # 模拟流式输出延迟
    
    def get_events(self, max_events: int = 10) -> List[StreamingEvent]:
        """获取最近的事件"""
        events = []
        
        try:
            while len(events) < max_events:
                event = self.event_queue.get_nowait()
                events.append(event)
        except queue.Empty:
            pass
        
        return events
    
    def add_websocket_client(self, websocket):
        """添加WebSocket客户端"""
        self.websocket_clients.add(websocket)
    
    def remove_websocket_client(self, websocket):
        """移除WebSocket客户端"""
        self.websocket_clients.discard(websocket)
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'status': self.status.value,
            'progress_info': self.progress_tracker.get_stage_info(),
            'content_length': len(self.current_content),
            'websocket_clients': len(self.websocket_clients),
            'event_queue_size': self.event_queue.qsize()
        }


# 全局流式处理器实例
_global_streaming_processor = None

def get_streaming_processor() -> StreamingProcessor:
    """获取全局流式处理器实例"""
    global _global_streaming_processor
    if _global_streaming_processor is None:
        _global_streaming_processor = StreamingProcessor()
    return _global_streaming_processor


# WebSocket服务器（可选）
async def websocket_handler(websocket, path):
    """WebSocket处理器"""
    processor = get_streaming_processor()
    processor.add_websocket_client(websocket)
    
    try:
        # 发送当前状态
        status_info = processor.get_status_info()
        await websocket.send(json.dumps({
            'event_type': 'status',
            'data': status_info
        }, ensure_ascii=False))
        
        # 保持连接
        await websocket.wait_closed()
        
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        processor.remove_websocket_client(websocket)


def start_websocket_server(host: str = "localhost", port: int = 8765):
    """启动WebSocket服务器"""
    return websockets.serve(websocket_handler, host, port)