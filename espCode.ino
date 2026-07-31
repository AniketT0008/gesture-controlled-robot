#include <WiFi.h>

// ---- WiFi credentials ----
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// ---- L298N pin definitions (updated wiring) ----
#define IN1 16
#define IN2 4
#define IN3 23
#define IN4 22
#define ENA 17
#define ENB 21

// ---- Speed settings (0-255) ----
int LEFT_SPEED = 120;    // corresponds to ENA side motor
int RIGHT_SPEED = 120;   // corresponds to ENB side motor
const int TURN_SPEED = 120;

WiFiServer server(80);

void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  stopMotors();

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! ESP32 IP address: ");
  Serial.println(WiFi.localIP());  // <-- this IP goes into your Python script

  server.begin();
}

void loop() {
  WiFiClient client = server.available();
  if (!client) return;

  String request = client.readStringUntil('\r');
  client.flush();

  request.trim();
  Serial.print("Command received: ");
  Serial.println(request);

  if (request.indexOf("FORWARD") >= 0) {
    moveForward();
  } else if (request.indexOf("BACKWARD") >= 0) {
    moveBackward();
  } else if (request.indexOf("LEFT") >= 0) {
    turnLeft();
  } else if (request.indexOf("RIGHT") >= 0) {
    turnRight();
  } else if (request.indexOf("STOP") >= 0) {
    stopMotors();
  }

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/plain");
  client.println();
  client.println("OK");
  client.stop();
}

// ---- Motor control functions ----

void moveForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, LEFT_SPEED);
  analogWrite(ENB, RIGHT_SPEED);
}

void moveBackward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENA, LEFT_SPEED);
  analogWrite(ENB, RIGHT_SPEED);
}

void turnLeft() {
  // left motor reverse, right motor forward -> pivot left
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, TURN_SPEED);
  analogWrite(ENB, TURN_SPEED);
}

void turnRight() {
  // right motor reverse, left motor forward -> pivot right
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENA, TURN_SPEED);
  analogWrite(ENB, TURN_SPEED);
}

void stopMotors() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
}