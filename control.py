import cv2
import mediapipe as mp
import joblib
import socket
import threading
import time
from collections import deque, Counter

# ---- CONFIG ----
ESP32_IP = "10.0.0.91"
ESP32_PORT = 80
MODEL_PATH = "gesture_classifier.pkl"
CONFIDENCE_THRESHOLD = 0.7      # ignore predictions below this confidence
SMOOTHING_WINDOW = 5            # frames to vote across before trusting a gesture
COMMAND_COOLDOWN = 0.3          # seconds between repeated sends of the same command
DRAW_SKELETON = True            # set False for a small extra speed boost

# gesture label -> ESP32 command string (must match what your Arduino code checks for)
LABEL_TO_COMMAND = {
    "Forward": "FORWARD",
    "Backward": "BACKWARD",
    "Left": "LEFT",
    "Right": "RIGHT",
    "Stop": "STOP",
}


# ---- Threaded video capture ----
class VideoStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)  # CAP_DSHOW = faster init/lower latency on Windows
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            with self.lock:
                self.ret, self.frame = ret, frame

    def read(self):
        with self.lock:
            return self.ret, self.frame.copy() if self.frame is not None else (self.ret, None)

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()


# ---- Setup MediaPipe ----
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    model_complexity=0  # fastest variant
)

# ---- Load trained classifier ----
clf = joblib.load(MODEL_PATH)


# ---- Send command to ESP32 over WiFi (non-blocking via thread so it never stalls the video loop) ----
def send_command(command):
    def _send():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((ESP32_IP, ESP32_PORT))
            sock.send((command + "\r\n").encode())
            sock.close()
            print(f"Sent: {command}")
        except Exception as e:
            print(f"Failed to send command: {e}")
    threading.Thread(target=_send, daemon=True).start()


# ---- Main loop ----
cv2.namedWindow("Robot Gesture Control", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Robot Gesture Control", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

vs = VideoStream(0)

recent_predictions = deque(maxlen=SMOOTHING_WINDOW)
current_command = None
last_send_time = 0

prev_time = time.time()

while True:
    ret, frame = vs.read()
    if not ret or frame is None:
        continue

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    predicted_label = None

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        if DRAW_SKELETON:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        landmarks_flat = []
        for lm in hand_landmarks.landmark:
            landmarks_flat.extend([lm.x, lm.y, lm.z])

        pred = clf.predict([landmarks_flat])[0]
        confidence = clf.predict_proba([landmarks_flat]).max()

        if confidence >= CONFIDENCE_THRESHOLD:
            predicted_label = pred

    recent_predictions.append(predicted_label)

    # majority vote over the smoothing window
    valid = [p for p in recent_predictions if p is not None]
    display_text = "No hand detected"

    if valid:
        majority_label, count = Counter(valid).most_common(1)[0]
        display_text = f"{majority_label} ({count}/{SMOOTHING_WINDOW})"

        if count >= SMOOTHING_WINDOW // 2 + 1:  # needs clear majority
            now = time.time()
            if majority_label != current_command or (now - last_send_time) > COMMAND_COOLDOWN:
                if majority_label != current_command:
                    current_command = majority_label
                command = LABEL_TO_COMMAND.get(majority_label)
                if command:
                    send_command(command)
                    last_send_time = now

    # FPS counter
    now = time.time()
    fps = 1.0 / (now - prev_time) if now != prev_time else 0.0
    prev_time = now

    cv2.putText(frame, f"Gesture: {display_text}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"Last command: {current_command}", (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    cv2.imshow("Robot Gesture Control", frame)
    cv2.setWindowProperty("Robot Gesture Control", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        send_command("STOP")  # safety stop on quit
        break

vs.stop()
cv2.destroyAllWindows()