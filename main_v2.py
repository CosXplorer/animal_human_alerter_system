# main_enhanced.py
import cv2
import yaml
import os
import time
import logging
from detector import Detector
from notifier import TelegramNotifier
from enhanced_utils import (
    IndividualTracker, 
    StreamHealthMonitor, 
    AlertRateLimiter,
    ErrorRecoveryManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment_variables():
    """Load environment variables from .env file if it exists"""
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            logger.info("Environment variables loaded")
    except Exception as e:
        logger.error(f"Failed to load environment variables: {e}")

def load_config():
    """Load configuration with error handling"""
    try:
        cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(cfg_path, 'r') as f:
            cfg = yaml.safe_load(f)
        logger.info("Configuration loaded successfully")
        return cfg
    except FileNotFoundError:
        logger.error("config.yaml not found, using defaults")
        return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def initialize_detector(model_path, conf_threshold, device):
    """Initialize detector with error handling"""
    try:
        detector = Detector(
            model_path=model_path, 
            conf_threshold=conf_threshold, 
            device=device
        )
        logger.info(f"Detector initialized: {model_path}")
        return detector
    except Exception as e:
        logger.critical(f"Failed to initialize detector: {e}", exc_info=True)
        raise

def initialize_notifier(telegram_cfg):
    """Initialize Telegram notifier with error handling"""
    try:
        telegram_enabled = telegram_cfg.get("enabled", False)
        telegram_token = os.getenv('TELEGRAM_TOKEN', telegram_cfg.get("token"))
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', telegram_cfg.get("chat_id"))
        
        if telegram_enabled and telegram_token and telegram_chat_id:
            notifier = TelegramNotifier(telegram_token, telegram_chat_id)
            # Test connection
            test_msg = "🚀 Detection system started"
            if notifier.send_message(test_msg):
                logger.info("Telegram notifier initialized and tested")
                return notifier
            else:
                logger.warning("Telegram notifier created but test message failed")
                return notifier
        else:
            logger.warning("Telegram notifier not configured")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize Telegram notifier: {e}")
        return None

def create_video_capture(stream_url, max_retries=3):
    """Create video capture with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to stream (attempt {attempt + 1}/{max_retries})...")
            cap = cv2.VideoCapture(stream_url)
            
            if not cap.isOpened():
                raise Exception("Failed to open stream")
            
            # Test read
            ret, frame = cap.read()
            if not ret:
                cap.release()
                raise Exception("Stream opened but cannot read frames")
            
            # Configure for low latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            logger.info(f"Stream connected: {frame.shape[1]}x{frame.shape[0]}")
            return cap
            
        except Exception as e:
            logger.error(f"Stream connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise

def draw_detections(frame, detections):
    """Draw bounding boxes with error handling"""
    try:
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{det['class_name']} {det['confidence']:.2f}"
            
            color = (0, 0, 255) if det['class_name'] == 'person' else (0, 255, 0)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    except Exception as e:
        logger.error(f"Error drawing detections: {e}")

def encode_frame_to_jpg(frame, quality=85):
    """Convert frame to JPEG bytes with error handling"""
    try:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, encoded_image = cv2.imencode('.jpg', frame, encode_params)
        if success:
            return encoded_image.tobytes()
        return None
    except Exception as e:
        logger.error(f"Error encoding frame: {e}")
        return None

def send_alert(notifier, detection, frame, tracker, rate_limiter, error_manager):
    """Send alert with comprehensive error handling"""
    try:
        # Check individual tracker cooldown
        should_alert, reason = tracker.should_alert(detection)
        if not should_alert:
            logger.debug(f"Alert skipped for {detection['class_name']}: {reason}")
            return False
        
        # Check rate limiter
        can_send, rate_reason = rate_limiter.can_send_alert()
        if not can_send:
            logger.warning(f"Alert rate limited: {rate_reason}")
            error_manager.record_error('rate_limit', rate_reason)
            return False
        
        # Build alert text
        text = (f"🚨 {detection['class_name'].title()} detected!\n"
                f"Confidence: {detection['confidence']:.2f}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.info(f"Sending alert: {text}")
        
        if notifier:
            # Draw detection on frame
            alert_frame = frame.copy()
            draw_detections(alert_frame, [detection])
            
            # Add timestamp
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(alert_frame, timestamp, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Encode and send
            photo_bytes = encode_frame_to_jpg(alert_frame)
            if photo_bytes:
                try:
                    success = notifier.send_photo(photo_bytes, text)
                    if success:
                        logger.info("✅ Alert sent successfully")
                        return True
                    else:
                        error_manager.record_error('telegram', 'Photo send returned False')
                        # Fallback to text-only
                        if notifier.send_message(text):
                            logger.info("✅ Fallback text alert sent")
                            return True
                except Exception as e:
                    error_manager.record_error('telegram', str(e))
                    logger.error(f"Telegram error: {e}")
            else:
                error_manager.record_error('encoding', 'Failed to encode frame')
        else:
            logger.warning("No notifier configured, alert logged only")
        
        return False
        
    except Exception as e:
        error_manager.record_error('alert_send', str(e))
        logger.error(f"Error sending alert: {e}", exc_info=True)
        return False

def main():
    logger.info("=" * 60)
    logger.info("🎯 Animal-Human Detection System Starting")
    logger.info("=" * 60)
    
    # Initialize error tracking
    error_manager = ErrorRecoveryManager()
    
    try:
        # Load configuration
        load_environment_variables()
        cfg = load_config()
        
        # Extract configuration
        STREAM_URL = os.getenv('STREAM_URL', cfg.get("stream_url"))
        CONF_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', cfg.get("confidence_threshold", 0.3)))
        COOLDOWN_SECONDS = int(os.getenv('ALERT_COOLDOWN_SECONDS', cfg.get("alert_cooldown_seconds", 60)))
        DEVICE = "cuda" if cfg.get("use_cuda", False) else "cpu"
        DISPLAY_LIVE_FEED = cfg.get("display_live_feed", True)
        WINDOW_NAME = cfg.get("window_name", "Animal-Human Detection")
        
        logger.info(f"Stream: {STREAM_URL}")
        logger.info(f"Confidence: {CONF_THRESHOLD}")
        logger.info(f"Cooldown: {COOLDOWN_SECONDS}s")
        logger.info(f"Device: {DEVICE}")
        
        # Initialize components
        detector = initialize_detector('yolov8n.pt', CONF_THRESHOLD, DEVICE)
        telegram_notifier = initialize_notifier(cfg.get("telegram", {}))
        
        # Initialize tracking and monitoring
        tracker = IndividualTracker(cooldown_seconds=COOLDOWN_SECONDS)
        stream_monitor = StreamHealthMonitor(max_failures=5, failure_window=60)
        rate_limiter = AlertRateLimiter(max_alerts_per_minute=10)
        
        # Connect to stream
        cap = create_video_capture(STREAM_URL)
        
        # Create display window
        if DISPLAY_LIVE_FEED:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 800, 600)
        
        # Main loop
        logger.info("🎥 Starting detection loop (Press 'q' to quit)")
        frame_count = 0
        detection_count = 0
        alert_count = 0
        start_time = time.time()
        last_stats_time = start_time
        
        while True:
            try:
                # Read frame
                ret, frame = cap.read()
                
                if not ret:
                    should_continue, error_msg = stream_monitor.record_failure()
                    logger.error(f"Frame read failed: {error_msg}")
                    
                    if not should_continue:
                        logger.critical("Too many stream failures, attempting reconnect...")
                        cap.release()
                        time.sleep(2)
                        cap = create_video_capture(STREAM_URL)
                        stream_monitor = StreamHealthMonitor()  # Reset monitor
                    else:
                        time.sleep(0.5)
                    continue
                
                stream_monitor.record_success()
                frame_count += 1
                current_time = time.time()
                
                # Resize for performance
                h, w = frame.shape[:2]
                if max(h, w) > 1280:
                    scale = 1280 / max(h, w)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                
                # Run detection
                alert_frame = frame.copy()
                detections = detector.predict_frame(frame)
                
                # Process each detection individually
                for detection in detections:
                    detection_count += 1
                    logger.debug(f"Detection: {detection['class_name']} @ {detection['confidence']:.2f}")
                    
                    # Try to send alert for this specific detection
                    if send_alert(telegram_notifier, detection, alert_frame, 
                                 tracker, rate_limiter, error_manager):
                        alert_count += 1
                
                # Draw detections
                display_frame = frame.copy()
                draw_detections(display_frame, detections)
                
                # Add debug overlay
                fps = frame_count / (current_time - start_time) if (current_time - start_time) > 0 else 0
                stream_health = stream_monitor.get_health_stats()
                rate_stats = rate_limiter.get_stats()
                active_cooldowns = tracker.get_active_cooldowns()
                
                debug_info = [
                    f"Frame: {frame_count} | FPS: {fps:.1f}",
                    f"Detections: {len(detections)} | Alerts: {alert_count}",
                    f"Success Rate: {stream_health.get('success_rate', 0):.1f}%",
                    f"Active Cooldowns: {len(active_cooldowns)}",
                    f"Alerts Remaining: {rate_stats.get('alerts_remaining', 0)}"
                ]
                
                y_offset = 30
                for info in debug_info:
                    cv2.putText(display_frame, info, (10, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    y_offset += 30
                
                # Display
                if DISPLAY_LIVE_FEED:
                    cv2.imshow(WINDOW_NAME, display_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("User requested quit")
                        break
                
                # Print stats every 30 seconds
                if current_time - last_stats_time > 30:
                    logger.info(f"Stats: Frames={frame_count}, Detections={detection_count}, "
                               f"Alerts={alert_count}, FPS={fps:.1f}")
                    logger.info(f"Error Summary: {error_manager.get_error_summary()}")
                    last_stats_time = current_time
                
                time.sleep(0.01)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                error_manager.record_error('main_loop', str(e))
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(1)  # Prevent tight error loop
                
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping detection (User Interrupt)")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        try:
            cap.release()
            if DISPLAY_LIVE_FEED:
                cv2.destroyAllWindows()
            
            # Print final statistics
            total_time = time.time() - start_time
            logger.info("\n" + "=" * 60)
            logger.info("FINAL STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Runtime: {total_time:.2f}s")
            logger.info(f"Frames: {frame_count}")
            logger.info(f"Detections: {detection_count}")
            logger.info(f"Alerts Sent: {alert_count}")
            logger.info(f"Avg FPS: {frame_count/total_time:.2f}" if total_time > 0 else "Avg FPS: 0.00")
            logger.info(f"Stream Health: {stream_monitor.get_health_stats()}")
            logger.info(f"Rate Limiter: {rate_limiter.get_stats()}")
            logger.info(f"Errors: {error_manager.get_error_summary()}")
            logger.info("=" * 60)
            logger.info("✅ System stopped successfully")
            
            # Send shutdown notification
            if telegram_notifier:
                telegram_notifier.send_message(
                    f"🛑 Detection system stopped\n"
                    f"Runtime: {total_time/60:.1f}min\n"
                    f"Alerts sent: {alert_count}"
                )
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    main()