"""
Performance monitoring utilities for the UI
"""
import time
from typing import Dict, List, Optional
from PySide6.QtCore import QTimer, QObject, Signal


class PerformanceMonitor(QObject):
    """Monitor UI performance metrics"""
    
    # Signals for performance events
    frame_time_updated = Signal(float)  # Frame time in ms
    memory_usage_updated = Signal(int)   # Memory usage in MB
    
    def __init__(self):
        super().__init__()
        self._frame_times: List[float] = []
        self._memory_samples: List[int] = []
        self._last_frame_time = 0
        self._monitoring = False
        
        # Timer for periodic monitoring
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._update_metrics)
        self._monitor_timer.setInterval(1000)  # Update every second
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self._monitoring = True
        self._monitor_timer.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self._monitoring = False
        self._monitor_timer.stop()
    
    def _update_metrics(self):
        """Update performance metrics"""
        if not self._monitoring:
            return
        
        # Calculate average frame time
        if self._frame_times:
            avg_frame_time = sum(self._frame_times) / len(self._frame_times)
            self.frame_time_updated.emit(avg_frame_time)
            self._frame_times.clear()
        
        # Calculate memory usage (simplified)
        try:
            import psutil
            process = psutil.Process()
            memory_mb = int(process.memory_info().rss / 1024 / 1024)
            self.memory_usage_updated.emit(memory_mb)
        except ImportError:
            # psutil not available, skip memory monitoring
            pass
    
    def record_frame_time(self, frame_time_ms: float):
        """Record a frame time measurement"""
        if self._monitoring:
            self._frame_times.append(frame_time_ms)
    
    def get_average_frame_time(self) -> float:
        """Get average frame time in milliseconds"""
        if not self._frame_times:
            return 0.0
        return sum(self._frame_times) / len(self._frame_times)
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get a summary of performance metrics"""
        return {
            'avg_frame_time_ms': self.get_average_frame_time(),
            'frame_samples': len(self._frame_times),
            'monitoring_active': self._monitoring
        }


class FrameTimer:
    """Simple frame timing utility"""
    
    def __init__(self):
        self._start_time = 0
        self._frame_times: List[float] = []
    
    def start_frame(self):
        """Start timing a frame"""
        self._start_time = time.perf_counter()
    
    def end_frame(self) -> float:
        """End timing a frame and return duration in milliseconds"""
        if self._start_time == 0:
            return 0.0
        
        frame_time = (time.perf_counter() - self._start_time) * 1000
        self._frame_times.append(frame_time)
        
        # Keep only last 60 frames
        if len(self._frame_times) > 60:
            self._frame_times.pop(0)
        
        self._start_time = 0
        return frame_time
    
    def get_average_frame_time(self) -> float:
        """Get average frame time in milliseconds"""
        if not self._frame_times:
            return 0.0
        return sum(self._frame_times) / len(self._frame_times)
    
    def get_fps(self) -> float:
        """Get average FPS"""
        avg_frame_time = self.get_average_frame_time()
        if avg_frame_time == 0:
            return 0.0
        return 1000.0 / avg_frame_time


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
