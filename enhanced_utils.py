# enhanced_utils.py
import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class IndividualTracker:
    """Track individual detections with spatial cooldowns"""
    
    def __init__(self, cooldown_seconds=60, distance_threshold=100):
        self.cooldown_seconds = cooldown_seconds
        self.distance_threshold = distance_threshold
        # Store: {(class_name, spatial_id): last_alert_time}
        self.last_alerts = {}
        self.spatial_grid_size = 200  # pixels for spatial binning
        
    def _get_bbox_center(self, bbox):
        """Calculate center point of bounding box"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def _get_spatial_id(self, bbox):
        """Convert bbox to spatial grid ID for proximity detection"""
        cx, cy = self._get_bbox_center(bbox)
        grid_x = int(cx / self.spatial_grid_size)
        grid_y = int(cy / self.spatial_grid_size)
        return (grid_x, grid_y)
    
    def _calculate_distance(self, bbox1, bbox2):
        """Calculate distance between two bounding boxes"""
        cx1, cy1 = self._get_bbox_center(bbox1)
        cx2, cy2 = self._get_bbox_center(bbox2)
        return np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
    
    def should_alert(self, detection: Dict) -> Tuple[bool, str]:
        """
        Check if we should alert for this detection.
        Returns: (should_alert, reason)
        """
        try:
            class_name = detection['class_name']
            bbox = detection['bbox']
            current_time = time.time()
            
            # Find if this detection is close to any recent alerts
            spatial_id = self._get_spatial_id(bbox)
            nearby_keys = [
                (class_name, (spatial_id[0] + dx, spatial_id[1] + dy))
                for dx in [-1, 0, 1] for dy in [-1, 0, 1]
            ]
            
            # Check all nearby spatial regions
            for key in nearby_keys:
                if key in self.last_alerts:
                    time_since_alert = current_time - self.last_alerts[key]
                    if time_since_alert < self.cooldown_seconds:
                        remaining = self.cooldown_seconds - time_since_alert
                        return False, f"Cooldown active ({remaining:.0f}s remaining)"
            
            # New detection - record it
            key = (class_name, spatial_id)
            self.last_alerts[key] = current_time
            
            # Clean up old entries (older than cooldown period)
            self._cleanup_old_alerts(current_time)
            
            return True, "New detection"
            
        except Exception as e:
            logger.error(f"Error in should_alert: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def _cleanup_old_alerts(self, current_time):
        """Remove alerts older than cooldown period"""
        try:
            keys_to_remove = [
                key for key, timestamp in self.last_alerts.items()
                if current_time - timestamp > self.cooldown_seconds * 2
            ]
            for key in keys_to_remove:
                del self.last_alerts[key]
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
    
    def get_active_cooldowns(self) -> List[Dict]:
        """Get list of active cooldowns for debugging"""
        try:
            current_time = time.time()
            active = []
            for (class_name, spatial_id), timestamp in self.last_alerts.items():
                remaining = self.cooldown_seconds - (current_time - timestamp)
                if remaining > 0:
                    active.append({
                        'class': class_name,
                        'location': spatial_id,
                        'remaining': remaining
                    })
            return active
        except Exception as e:
            logger.error(f"Error getting active cooldowns: {e}")
            return []


class StreamHealthMonitor:
    """Monitor stream health and handle reconnection"""
    
    def __init__(self, max_failures=5, failure_window=60):
        self.max_failures = max_failures
        self.failure_window = failure_window
        self.failure_times = []
        self.total_frames = 0
        self.failed_frames = 0
        self.last_success_time = time.time()
        
    def record_success(self):
        """Record successful frame read"""
        self.total_frames += 1
        self.last_success_time = time.time()
        
    def record_failure(self) -> Tuple[bool, str]:
        """
        Record failed frame read.
        Returns: (should_continue, error_message)
        """
        try:
            self.failed_frames += 1
            current_time = time.time()
            self.failure_times.append(current_time)
            
            # Remove old failures outside the window
            self.failure_times = [
                t for t in self.failure_times 
                if current_time - t < self.failure_window
            ]
            
            # Check if we've hit the failure threshold
            if len(self.failure_times) >= self.max_failures:
                return False, f"Stream failed {self.max_failures} times in {self.failure_window}s"
            
            # Check if stream has been dead too long
            time_since_success = current_time - self.last_success_time
            if time_since_success > 30:
                return False, f"No successful frames for {time_since_success:.0f}s"
            
            return True, f"Temporary failure ({len(self.failure_times)}/{self.max_failures})"
            
        except Exception as e:
            logger.error(f"Error in record_failure: {e}", exc_info=True)
            return True, "Error tracking failure"
    
    def get_health_stats(self) -> Dict:
        """Get stream health statistics"""
        try:
            if self.total_frames == 0:
                success_rate = 0
            else:
                success_rate = ((self.total_frames - self.failed_frames) / self.total_frames) * 100
            
            return {
                'total_frames': self.total_frames,
                'failed_frames': self.failed_frames,
                'success_rate': success_rate,
                'recent_failures': len(self.failure_times),
                'time_since_success': time.time() - self.last_success_time
            }
        except Exception as e:
            logger.error(f"Error getting health stats: {e}")
            return {}


class AlertRateLimiter:
    """Prevent alert spam with rate limiting"""
    
    def __init__(self, max_alerts_per_minute=10):
        self.max_alerts_per_minute = max_alerts_per_minute
        self.alert_times = []
        self.total_alerts = 0
        self.blocked_alerts = 0
        
    def can_send_alert(self) -> Tuple[bool, str]:
        """
        Check if we can send an alert.
        Returns: (can_send, reason)
        """
        try:
            current_time = time.time()
            
            # Remove alerts older than 1 minute
            self.alert_times = [
                t for t in self.alert_times 
                if current_time - t < 60
            ]
            
            # Check rate limit
            if len(self.alert_times) >= self.max_alerts_per_minute:
                self.blocked_alerts += 1
                return False, f"Rate limit reached ({self.max_alerts_per_minute}/min)"
            
            # Record this alert
            self.alert_times.append(current_time)
            self.total_alerts += 1
            return True, "Alert allowed"
            
        except Exception as e:
            logger.error(f"Error in can_send_alert: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics"""
        try:
            return {
                'total_alerts': self.total_alerts,
                'blocked_alerts': self.blocked_alerts,
                'recent_alerts': len(self.alert_times),
                'alerts_remaining': max(0, self.max_alerts_per_minute - len(self.alert_times))
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


class ErrorRecoveryManager:
    """Manage error recovery strategies"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_errors = {}
        self.recovery_strategies = {
            'stream_read': self._recover_stream_read,
            'detection': self._recover_detection,
            'telegram': self._recover_telegram,
            'model_load': self._recover_model_load
        }
        
    def record_error(self, error_type: str, error_msg: str):
        """Record an error occurrence"""
        try:
            self.error_counts[error_type] += 1
            self.last_errors[error_type] = {
                'message': error_msg,
                'time': time.time(),
                'count': self.error_counts[error_type]
            }
            logger.error(f"{error_type}: {error_msg} (occurrence #{self.error_counts[error_type]})")
        except Exception as e:
            logger.error(f"Error recording error: {e}")
    
    def should_retry(self, error_type: str, max_retries: int = 3) -> bool:
        """Check if we should retry after an error"""
        try:
            return self.error_counts.get(error_type, 0) < max_retries
        except Exception as e:
            logger.error(f"Error checking retry status: {e}")
            return False
    
    def _recover_stream_read(self) -> str:
        """Recovery strategy for stream read failures"""
        return "Wait 2s, then recreate VideoCapture object"
    
    def _recover_detection(self) -> str:
        """Recovery strategy for detection failures"""
        return "Skip frame and continue with next frame"
    
    def _recover_telegram(self) -> str:
        """Recovery strategy for Telegram failures"""
        return "Log alert locally, continue processing"
    
    def _recover_model_load(self) -> str:
        """Recovery strategy for model load failures"""
        return "Critical error - cannot continue without model"
    
    def get_recovery_strategy(self, error_type: str) -> str:
        """Get recommended recovery strategy"""
        try:
            strategy_func = self.recovery_strategies.get(error_type)
            if strategy_func:
                return strategy_func()
            return "No specific recovery strategy defined"
        except Exception as e:
            logger.error(f"Error getting recovery strategy: {e}")
            return "Error determining recovery strategy"
    
    def get_error_summary(self) -> Dict:
        """Get summary of all errors"""
        try:
            return {
                'error_counts': dict(self.error_counts),
                'last_errors': {
                    k: {
                        'message': v['message'],
                        'count': v['count'],
                        'time_ago': time.time() - v['time']
                    }
                    for k, v in self.last_errors.items()
                }
            }
        except Exception as e:
            logger.error(f"Error getting error summary: {e}")
            return {}