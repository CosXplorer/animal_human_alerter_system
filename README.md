🎯 Animal-Human Detection System
A real-time computer vision system that detects humans and animals in video streams and sends instant Telegram alerts with photos. Built with YOLOv8 and designed for reliable 24/7 operation with comprehensive error handling.
✨ Features

Real-time Detection: Monitors video streams for humans and animals using YOLOv8
Individual Tracking: Tracks each person/animal separately with spatial cooldowns
Instant Alerts: Sends Telegram notifications with annotated photos
Robust Error Handling: Auto-recovery from stream failures, API errors, and network issues
Smart Rate Limiting: Prevents alert spam while catching new detections
Health Monitoring: Tracks system performance and stream reliability
Detailed Logging: Comprehensive logs for debugging and monitoring

📋 Requirements
Hardware

Camera with RTSP/HTTP video stream support
Computer with webcam (for testing) or network camera

Software

Python 3.8+
OpenCV
YOLOv8 (Ultralytics)
Telegram Bot

🚀 Installation
1. Clone the Repository
bashgit clone <your-repo-url>
cd detection-system
2. Install Dependencies
bashpip install -r requirements.txt
requirements.txt:
ultralytics>=8.0.0
opencv-python>=4.8.0
PyYAML>=6.0
requests>=2.31.0
numpy>=1.24.0
3. Create Telegram Bot

Open Telegram and search for @BotFather
Send /newbot and follow the instructions
Save your bot token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
Start a chat with your bot and send any message
Get your chat ID by visiting: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

4. Configure the System
Option A: Using config.yaml (recommended for testing)
yamlstream_url: "http://10.81.57.57:8080/video"  # Your camera stream URL
confidence_threshold: 0.3
alert_cooldown_seconds: 60
use_cuda: false  # Set to true if you have NVIDIA GPU

display_live_feed: true
window_name: "Animal-Human Detection"

telegram:
  enabled: true
  token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"
  send_photos: true
Option B: Using .env file (recommended for production)
Create a .env file in the project directory:
bashSTREAM_URL=http://10.81.57.57:8080/video
CONFIDENCE_THRESHOLD=0.3
ALERT_COOLDOWN_SECONDS=60
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
📁 Project Structure
detection-system/
├── main_enhanced.py         # Main application with error handling
├── detector_v2.py           # YOLO detection logic
├── notifier.py             # Telegram notification handler
├── enhanced_utils.py       # Tracking & error handling utilities
├── config.yaml             # Configuration file
├── .env                    # Environment variables (optional)
├── requirements.txt        # Python dependencies
├── detection.log          # Application logs (auto-generated)
└── README.md              # This file
🎮 Usage
Basic Usage
bashpython main_enhanced.py
Controls

q: Quit the application
Ctrl+C: Stop gracefully

Monitoring Logs
bash# View live logs
tail -f detection.log

# View recent errors
grep ERROR detection.log
⚙️ Configuration Options
Detection Settings
ParameterDefaultDescriptionconfidence_threshold0.3Minimum confidence for detections (0.0-1.0)alert_cooldown_seconds60Cooldown between alerts for same individualuse_cudafalseEnable GPU acceleration (requires CUDA)
Display Settings
ParameterDefaultDescriptiondisplay_live_feedtrueShow live video windowwindow_name"Animal-Human Detection"Display window title
Advanced Settings (in enhanced_utils.py)
ParameterDefaultDescriptiondistance_threshold100Pixel distance for same individualspatial_grid_size200Grid size for spatial trackingmax_alerts_per_minute10Rate limit for alertsmax_failures5Max stream failures before reconnect
🔧 Troubleshooting
Issue: Stream Connection Failed
Solutions:

Check camera is powered on and connected to network
Verify stream URL is correct (try opening in VLC)
Check firewall settings
Reduce confidence threshold if camera quality is poor

Issue: No Alerts Received
Solutions:

Verify Telegram bot token and chat ID are correct
Check detection.log for Telegram API errors
Ensure you've started a chat with your bot
Test bot manually: send message to bot and check response

Issue: Too Many False Alerts
Solutions:

Increase confidence_threshold (try 0.4 or 0.5)
Increase alert_cooldown_seconds (try 120 or 180)
Adjust distance_threshold in enhanced_utils.py

Issue: Missing Detections
Solutions:

Lower confidence_threshold (try 0.2)
Check lighting conditions
Ensure objects are not too small in frame
Reduce alert_cooldown_seconds if needed

Issue: High CPU Usage
Solutions:

Enable GPU acceleration: set use_cuda: true
Reduce frame resolution in code
Increase frame skip interval
Disable display_live_feed for headless operation

📊 Understanding the System
How Individual Tracking Works
The system divides the camera view into a spatial grid. Each detection is assigned to a grid cell based on its center point. Cooldowns are applied per (class, grid_cell) combination, so:

Person at left side of frame → triggers alert
Person at right side of frame → triggers separate alert
Same person moves slightly → no new alert (cooldown active)
Same person moves far → may trigger new alert (different grid cell)

Error Recovery Strategies
Error TypeRecovery StrategyStream read failureWait 2s, retry, then reconnect after 5 failuresDetection errorSkip frame, continue with nextTelegram failureLog locally, fallback to text-onlyModel load failureCritical error - system stopsRate limit hitQueue alert, send when limit resets
Alert Rate Limiting

Default: 10 alerts per minute maximum
Prevents spam during high activity
Blocked alerts are logged for review
Rate limit resets every 60 seconds

📈 Performance Tips

GPU Acceleration: Set use_cuda: true for 5-10x speed improvement
Frame Size: Reduce resolution for faster processing (done automatically)
Confidence Threshold: Balance between speed and accuracy
Display Mode: Disable live feed for headless servers
Network: Use wired connection for camera stream

🔒 Security Notes

Never commit .env file or tokens to version control
Use environment variables for production deployments
Restrict Telegram bot access to specific chat IDs
Monitor detection.log regularly for suspicious activity

📝 Logging
The system creates detailed logs in detection.log:
2024-01-15 10:30:15 - INFO - Stream connected: 1920x1080
2024-01-15 10:30:20 - INFO - Detection: person @ 0.85
2024-01-15 10:30:20 - INFO - ✅ Alert sent successfully
2024-01-15 10:30:25 - WARNING - Alert skipped for person: Cooldown active (55s remaining)
Log Levels:

INFO: Normal operations
WARNING: Non-critical issues
ERROR: Recoverable errors
CRITICAL: Fatal errors

🤝 Contributing
Contributions are welcome! Please:

Fork the repository
Create a feature branch
Add tests for new features
Submit a pull request

📄 License
[Your chosen license - e.g., MIT]
🆘 Support
For issues and questions:

Check detection.log for error details
Review troubleshooting section above
Open an issue on GitHub with:

Log excerpt showing the error
Your configuration (remove sensitive tokens)
Steps to reproduce



🎓 Detected Classes
Humans: person
Animals: bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe
To add more classes, modify the animal_classes list in detector_v2.py.
🔄 Updates & Maintenance
Updating YOLOv8
bashpip install --upgrade ultralytics
Checking System Status
bash# View recent activity
tail -n 50 detection.log

# Count today's detections
grep "Detection:" detection.log | grep "$(date +%Y-%m-%d)" | wc -l

# View error summary
grep -A 2 "Error Summary" detection.log | tail -n 10
🚀 Future Enhancements

 Web dashboard for monitoring
 Email notifications
 Multiple camera support
 Cloud storage for detection images
 Mobile app
 Face recognition for known individuals
 Activity heatmaps
 Custom alert zones


Version: 2.0
Last Updated: 2024
Status: Production Ready
For more information, visit the project repository.
