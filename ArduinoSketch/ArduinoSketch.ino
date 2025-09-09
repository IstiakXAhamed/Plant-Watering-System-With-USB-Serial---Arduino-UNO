const int relayPin = 3;
const int sensorPin = A0;

bool forceMode = false;
bool forceState = false;

int autoMin = 40;
int autoMax = 85;

const int sampleCount = 10;
const int delaySample = 50;

const int sensorDry = 890;   // Dry reading
const int sensorWet = 500;   // Wet reading

String inputBuffer = "";  // For reliable serial command reading

void setup() {
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW);
  Serial.begin(9600);
}

void loop() {
  // --- Smooth readings ---
  int sum = 0;
  for(int i=0; i<sampleCount; i++){
    sum += analogRead(sensorPin);
    delay(delaySample);
  }
  int raw = sum / sampleCount;

  int moisturePercent = map(raw, sensorDry, sensorWet, 0, 100);
  moisturePercent = constrain(moisturePercent, 0, 100);

  // --- Auto pump control ---
  if(!forceMode){
    if(moisturePercent < autoMin) digitalWrite(relayPin, HIGH);
    else if(moisturePercent > autoMax) digitalWrite(relayPin, LOW);
  } else {
    digitalWrite(relayPin, forceState ? HIGH : LOW);
  }

  // --- Send data to dashboard ---
  String relayState = digitalRead(relayPin) ? "ON" : "OFF";
  Serial.print("LEVEL:");
  Serial.print(moisturePercent);
  Serial.print(",RELAY:");
  Serial.println(relayState);

  // --- Reliable serial command handling ---
  while(Serial.available()){
    char c = Serial.read();
    if(c == '\n'){
      processCommand(inputBuffer);
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}

// --- Process commands ---
void processCommand(String cmd){
  cmd.trim();
  if(cmd == "FORCE_ON"){ forceMode=true; forceState=true; }
  else if(cmd == "FORCE_OFF"){ forceMode=true; forceState=false; }
  else if(cmd == "AUTO"){ forceMode=false; }
  else if(cmd.startsWith("SET_MIN:")){
    int val = cmd.substring(8).toInt();
    if(val >= 0 && val < autoMax) autoMin = val;
    Serial.print("ACK_MIN:");
    Serial.println(autoMin);
  }
  else if(cmd.startsWith("SET_MAX:")){
    int val = cmd.substring(8).toInt();
    if(val <= 100 && val > autoMin) autoMax = val;
    Serial.print("ACK_MAX:");
    Serial.println(autoMax);
  }
}
