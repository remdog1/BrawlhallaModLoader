"""
Performance optimization and animation framework for the UI
"""
import time
from typing import Dict, List, Optional, Callable, Any
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, QObject, Signal, QRect, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap, QTransform


class PerformanceCache:
    """Centralized caching system for UI elements"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._max_age = 300  # 5 minutes cache age
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached item if still valid"""
        if key in self._cache:
            if time.time() - self._timestamps[key] < self._max_age:
                return self._cache[key]
            else:
                # Expired, remove it
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Cache an item with timestamp"""
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached items"""
        self._cache.clear()
        self._timestamps.clear()
    
    def invalidate(self, key: str) -> None:
        """Remove specific cached item"""
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]


class AnimationManager(QObject):
    """Centralized animation management system"""
    
    def __init__(self):
        super().__init__()
        self._active_animations: Dict[QWidget, List[QPropertyAnimation]] = {}
        self._animation_queue: List[Dict] = []
        self._processing_queue = False
    
    def bounce_scale(self, widget: QWidget, scale_factor: float = 1.1, duration: int = 200) -> None:
        """Create a bounce scale animation"""
        if not widget:
            return
            
        # Stop any existing animations on this widget
        self.stop_animations(widget)
        
        # Create scale animation
        scale_anim = QPropertyAnimation(widget, b"geometry")
        scale_anim.setDuration(duration)
        scale_anim.setEasingCurve(QEasingCurve.OutBounce)
        
        # Get current geometry
        current_rect = widget.geometry()
        center = current_rect.center()
        
        # Calculate scaled size
        scaled_width = int(current_rect.width() * scale_factor)
        scaled_height = int(current_rect.height() * scale_factor)
        
        # Center the scaled rectangle
        scaled_rect = QRect(
            center.x() - scaled_width // 2,
            center.y() - scaled_height // 2,
            scaled_width,
            scaled_height
        )
        
        scale_anim.setStartValue(current_rect)
        scale_anim.setEndValue(scaled_rect)
        
        # Create return animation
        return_anim = QPropertyAnimation(widget, b"geometry")
        return_anim.setDuration(duration)
        return_anim.setEasingCurve(QEasingCurve.InOutQuad)
        return_anim.setStartValue(scaled_rect)
        return_anim.setEndValue(current_rect)
        
        # Chain animations
        scale_anim.finished.connect(lambda: return_anim.start())
        
        # Store animations
        self._active_animations[widget] = [scale_anim, return_anim]
        
        # Start animation
        scale_anim.start()
    
    def fade_in(self, widget: QWidget, duration: int = 300) -> None:
        """Fade in animation"""
        if not widget:
            return
            
        # Create opacity effect
        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)
        
        # Create animation
        fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        fade_anim.setDuration(duration)
        fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        
        # Store animation
        if widget not in self._active_animations:
            self._active_animations[widget] = []
        self._active_animations[widget].append(fade_anim)
        
        # Start animation
        fade_anim.start()
    
    def fade_out(self, widget: QWidget, duration: int = 300, callback: Optional[Callable] = None) -> None:
        """Fade out animation with optional callback"""
        if not widget:
            return
            
        # Get or create opacity effect
        opacity_effect = widget.graphicsEffect()
        if not isinstance(opacity_effect, QGraphicsOpacityEffect):
            opacity_effect = QGraphicsOpacityEffect()
            widget.setGraphicsEffect(opacity_effect)
        
        # Create animation
        fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        fade_anim.setDuration(duration)
        fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        
        # Add callback if provided
        if callback:
            fade_anim.finished.connect(callback)
        
        # Store animation
        if widget not in self._active_animations:
            self._active_animations[widget] = []
        self._active_animations[widget].append(fade_anim)
        
        # Start animation
        fade_anim.start()
    
    def smooth_hover_scale(self, widget: QWidget, scale_factor: float = 1.05, duration: int = 150) -> None:
        """Smooth hover scale animation"""
        if not widget:
            return
            
        # Stop any existing animations on this widget
        self.stop_animations(widget)
        
        # Create scale animation
        scale_anim = QPropertyAnimation(widget, b"geometry")
        scale_anim.setDuration(duration)
        scale_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Get current geometry
        current_rect = widget.geometry()
        center = current_rect.center()
        
        # Calculate scaled size
        scaled_width = int(current_rect.width() * scale_factor)
        scaled_height = int(current_rect.height() * scale_factor)
        
        # Center the scaled rectangle
        scaled_rect = QRect(
            center.x() - scaled_width // 2,
            center.y() - scaled_height // 2,
            scaled_width,
            scaled_height
        )
        
        scale_anim.setStartValue(current_rect)
        scale_anim.setEndValue(scaled_rect)
        
        # Store animation
        self._active_animations[widget] = [scale_anim]
        
        # Start animation
        scale_anim.start()
    
    def smooth_hover_return(self, widget: QWidget, duration: int = 150) -> None:
        """Return from hover scale animation"""
        if not widget:
            return
            
        # Stop any existing animations on this widget
        self.stop_animations(widget)
        
        # Create return animation
        return_anim = QPropertyAnimation(widget, b"geometry")
        return_anim.setDuration(duration)
        return_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Get current geometry and calculate original size
        current_rect = widget.geometry()
        center = current_rect.center()
        
        # Calculate original size (assuming 1.05 scale factor)
        original_width = int(current_rect.width() / 1.05)
        original_height = int(current_rect.height() / 1.05)
        
        # Center the original rectangle
        original_rect = QRect(
            center.x() - original_width // 2,
            center.y() - original_height // 2,
            original_width,
            original_height
        )
        
        return_anim.setStartValue(current_rect)
        return_anim.setEndValue(original_rect)
        
        # Store animation
        self._active_animations[widget] = [return_anim]
        
        # Start animation
        return_anim.start()
    
    def stop_animations(self, widget: QWidget) -> None:
        """Stop all animations for a widget"""
        if widget in self._active_animations:
            for anim in self._active_animations[widget]:
                anim.stop()
            del self._active_animations[widget]
    
    def stop_all_animations(self) -> None:
        """Stop all active animations"""
        for widget, animations in self._active_animations.items():
            for anim in animations:
                anim.stop()
        self._active_animations.clear()


class OptimizedLayoutManager:
    """Optimized layout management with caching and debouncing"""
    
    def __init__(self):
        self._layout_cache: Dict[str, Any] = {}
        self._update_timers: Dict[QWidget, QTimer] = {}
        self._last_sizes: Dict[QWidget, QSize] = {}
    
    def debounced_update(self, widget: QWidget, update_func: Callable, delay: int = 50) -> None:
        """Debounced layout update to prevent excessive recalculations"""
        if widget in self._update_timers:
            self._update_timers[widget].stop()
        
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(update_func)
        timer.start(delay)
        
        self._update_timers[widget] = timer
    
    def should_update_layout(self, widget: QWidget, new_size: QSize) -> bool:
        """Check if layout update is needed based on size change"""
        if widget not in self._last_sizes:
            self._last_sizes[widget] = new_size
            return True
        
        last_size = self._last_sizes[widget]
        # Only update if size changed significantly (more than 10 pixels)
        size_changed = abs(new_size.width() - last_size.width()) > 10 or \
                      abs(new_size.height() - last_size.height()) > 10
        
        if size_changed:
            self._last_sizes[widget] = new_size
            return True
        
        return False
    
    def cache_layout_result(self, key: str, result: Any) -> None:
        """Cache layout calculation result"""
        self._layout_cache[key] = result
    
    def get_cached_layout(self, key: str) -> Optional[Any]:
        """Get cached layout result"""
        return self._layout_cache.get(key)
    
    def clear_cache(self) -> None:
        """Clear all cached layout results"""
        self._layout_cache.clear()
        self._last_sizes.clear()


class BackgroundOptimizer:
    """Optimized background image management"""
    
    def __init__(self):
        self._cached_pixmaps: Dict[str, QPixmap] = {}
        self._scaled_cache: Dict[str, Dict[QSize, QPixmap]] = {}
    
    def get_optimized_pixmap(self, path: str, size: QSize) -> Optional[QPixmap]:
        """Get optimized pixmap with caching"""
        if not path:
            return None
        
        # Check scaled cache first
        if path in self._scaled_cache:
            if size in self._scaled_cache[path]:
                return self._scaled_cache[path][size]
        
        # Load original pixmap if not cached
        if path not in self._cached_pixmaps:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None
            self._cached_pixmaps[path] = pixmap
        
        # Scale and cache
        original_pixmap = self._cached_pixmaps[path]
        scaled_pixmap = original_pixmap.scaled(
            size, 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        # Cache the scaled version
        if path not in self._scaled_cache:
            self._scaled_cache[path] = {}
        self._scaled_cache[path][size] = scaled_pixmap
        
        return scaled_pixmap
    
    def clear_cache(self) -> None:
        """Clear all cached pixmaps"""
        self._cached_pixmaps.clear()
        self._scaled_cache.clear()


# Global instances
performance_cache = PerformanceCache()
animation_manager = AnimationManager()
layout_manager = OptimizedLayoutManager()
background_optimizer = BackgroundOptimizer()
