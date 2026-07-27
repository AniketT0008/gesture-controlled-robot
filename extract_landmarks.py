import cv2
import mediapipe as mp
import os
import csv

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5)

DATASET_DIR = r"C:\Users\school\Downloads\DataSet"
GESTURES = ["Forward", "Backward", "Left", "Right", "Stop"]
OUTPUT_FILE = "gesture_data.csv"

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    header = [f"{axis}{i}" for i in range(21) for axis in ('x', 'y', 'z')] + ["label"]
    writer.writerow(header)

    total_written = 0
    total_skipped = 0

    for gesture in GESTURES:
        folder = os.path.join(DATASET_DIR, gesture)
        if not os.path.isdir(folder):
            print(f"WARNING: folder not found: {folder}")
            continue

        images = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        written = 0
        skipped = 0

        for img_name in images:
            img_path = os.path.join(folder, img_name)
            img = cv2.imread(img_path)
            if img is None:
                skipped += 1
                continue

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            if not results.multi_hand_landmarks:
                skipped += 1
                continue

            hand_landmarks = results.multi_hand_landmarks[0]
            landmarks_flat = []
            for lm in hand_landmarks.landmark:
                landmarks_flat.extend([lm.x, lm.y, lm.z])

            writer.writerow(landmarks_flat + [gesture])
            written += 1

        print(f"{gesture}: {written} written, {skipped} skipped (no hand detected)")
        total_written += written
        total_skipped += skipped

print(f"\nTotal: {total_written} samples written, {total_skipped} images skipped")
print(f"Saved to {OUTPUT_FILE}")