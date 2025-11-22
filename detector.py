# detector.py
from ultralytics import YOLO
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Detector:
    def __init__(self, model_path='yolov8n.pt', conf_threshold=0.4, device='cpu'):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = device
        
        # Define classes of interest - ONLY humans and animals
        self.human_classes = ['person']
        self.animal_classes = [
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 
            'bear', 'zebra', 'giraffe', 'bird', 'bear', 'cat', 'dog'
        ]
        
        # Combine all classes we're interested in
        self.target_classes = self.human_classes + self.animal_classes
        
        print(f"Detector initialized for humans and animals only")
        print(f"Human classes: {self.human_classes}")
        print(f"Animal classes: {self.animal_classes}")

    def predict_frame(self, frame):
        """Run detection on a single frame and return filtered detections"""
        try:
            results = self.model(frame, conf=self.conf_threshold, device=self.device, verbose=False)
            
            detections = []
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        confidence = box.conf.item()
                        class_id = int(box.cls.item())
                        class_name = self.model.names[class_id]
                        
                        # Only process humans and animals
                        if class_name in self.target_classes:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            
                            detections.append({
                                'bbox': [x1, y1, x2, y2],
                                'confidence': confidence,
                                'class_name': class_name,
                                'class_id': class_id
                            })
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {str(e)}")
            return []

    def classify_group(self, detections):
        """Classify detections into human/animal groups"""
        human_detected = False
        animal_detected = False
        details = []

        for det in detections:
            class_name = det['class_name']
            details.append({
                'class_name': class_name,
                'confidence': det['confidence']
            })
            
            if class_name in self.human_classes:
                human_detected = True
            elif class_name in self.animal_classes:
                animal_detected = True

        return {
            'human': human_detected,
            'animal': animal_detected,
            'details': details
        }