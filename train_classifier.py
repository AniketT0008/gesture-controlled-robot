import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
import joblib

df = pd.read_csv("gesture_data.csv")
X = df.drop("label", axis=1)
y = df["label"]

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

clf = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=42)
clf.fit(X_train, y_train)

val_acc = accuracy_score(y_val, clf.predict(X_val))
print(f"Validation accuracy: {val_acc*100:.1f}%")

joblib.dump(clf, "gesture_classifier.pkl")
print("Saved model as gesture_classifier.pkl")