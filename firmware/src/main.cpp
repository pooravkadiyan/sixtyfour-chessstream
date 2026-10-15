/**
 * ChessStream India - ESP32 Firmware
 * 
 * Low-cost electronic chess board for tournament streaming
 * 
 * Hardware:
 * - ESP32-WROOM-32E
 * - 4x CD74HC4067 multiplexers
 * - 64x Reed switches
 * 
 * Features:
 * - Scans 64 squares via multiplexed reed switches
 * - Detects piece lift/place events
 * - Broadcasts moves via WebSocket
 * - Supports LiveChess protocol
 * - OTA firmware updates
 * 
 * License: MIT
 * Author: Monara Ventures (Poorav Kadiyan)
 */

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <EEPROM.h>

// ============== Configuration ==============

// WiFi credentials (will be configurable via AP mode)
const char* DEFAULT_SSID = "ChessStream";
const char* DEFAULT_PASSWORD = "chess123";

// Board identification
const char* BOARD_ID = "CS001";
const char* FIRMWARE_VERSION = "0.1.0";

// ============== Pin Definitions ==============

// Multiplexer signal pins (directly connected to ESP32 ADC)
#define MUX1_SIG 32
#define MUX2_SIG 33
#define MUX3_SIG 34
#define MUX4_SIG 35

// Multiplexer select pins (directly connected to all MUX select inputs)
#define SEL_A 25
#define SEL_B 26
#define SEL_C 27
#define SEL_D 14

// Status LED
#define LED_PIN 2

// ============== Constants ==============

#define NUM_SQUARES 64
#define NUM_ROWS 8
#define NUM_COLS 8
#define DEBOUNCE_MS 50
#define SCAN_INTERVAL_MS 10
#define WEBSOCKET_PORT 81

// Square names for notation
const char* SQUARE_NAMES[64] = {
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
    "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
    "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
    "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
    "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
    "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
    "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
    "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8"
};

// Initial board state (1 = piece present, 0 = empty)
// Standard chess starting position
const uint8_t INITIAL_BOARD[64] = {
    1, 1, 1, 1, 1, 1, 1, 1,  // Row 1 (white pieces)
    1, 1, 1, 1, 1, 1, 1, 1,  // Row 2 (white pawns)
    0, 0, 0, 0, 0, 0, 0, 0,  // Row 3
    0, 0, 0, 0, 0, 0, 0, 0,  // Row 4
    0, 0, 0, 0, 0, 0, 0, 0,  // Row 5
    0, 0, 0, 0, 0, 0, 0, 0,  // Row 6
    1, 1, 1, 1, 1, 1, 1, 1,  // Row 7 (black pawns)
    1, 1, 1, 1, 1, 1, 1, 1   // Row 8 (black pieces)
};

// ============== Global State ==============

// Current board state (reed switch readings)
uint8_t currentBoard[NUM_SQUARES];
uint8_t previousBoard[NUM_SQUARES];

// Debounce tracking
unsigned long lastChangeTime[NUM_SQUARES];
uint8_t pendingState[NUM_SQUARES];

// Move detection
int liftedSquare = -1;  // Square where piece was lifted (-1 = none)
unsigned long liftTime = 0;

// Game state
bool gameInProgress = false;
int moveNumber = 0;
bool whiteToMove = true;

// WebSocket server
WebSocketsServer webSocket = WebSocketsServer(WEBSOCKET_PORT);

// ============== Function Declarations ==============

void setupPins();
void setupWiFi();
void setupWebSocket();
void scanBoard();
uint8_t readSquare(int square);
void setMuxChannel(int channel);
void processChanges();
void handleLift(int square);
void handlePlace(int square);
void broadcastMove(const char* from, const char* to);
void broadcastBoardState();
void webSocketEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length);
void blinkLED(int times, int delayMs);

// ============== Setup ==============

void setup() {
    Serial.begin(115200);
    Serial.println("\n\n=== ChessStream India ===");
    Serial.printf("Firmware: %s\n", FIRMWARE_VERSION);
    Serial.printf("Board ID: %s\n", BOARD_ID);
    
    setupPins();
    setupWiFi();
    setupWebSocket();
    
    // Initialize board state
    memcpy(currentBoard, INITIAL_BOARD, NUM_SQUARES);
    memcpy(previousBoard, INITIAL_BOARD, NUM_SQUARES);
    memset(lastChangeTime, 0, sizeof(lastChangeTime));
    
    // Initial scan
    scanBoard();
    
    Serial.println("Setup complete. Ready for games!");
    blinkLED(3, 200);
}

// ============== Main Loop ==============

void loop() {
    static unsigned long lastScan = 0;
    
    // Handle WebSocket events
    webSocket.loop();
    
    // Scan board at regular intervals
    if (millis() - lastScan >= SCAN_INTERVAL_MS) {
        lastScan = millis();
        scanBoard();
        processChanges();
    }
}

// ============== Pin Setup ==============

void setupPins() {
    // Multiplexer signal pins (input)
    pinMode(MUX1_SIG, INPUT);
    pinMode(MUX2_SIG, INPUT);
    pinMode(MUX3_SIG, INPUT);
    pinMode(MUX4_SIG, INPUT);
    
    // Multiplexer select pins (output)
    pinMode(SEL_A, OUTPUT);
    pinMode(SEL_B, OUTPUT);
    pinMode(SEL_C, OUTPUT);
    pinMode(SEL_D, OUTPUT);
    
    // Status LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    
    Serial.println("Pins configured");
}

// ============== WiFi Setup ==============

void setupWiFi() {
    Serial.printf("Connecting to WiFi: %s\n", DEFAULT_SSID);
    
    WiFi.mode(WIFI_STA);
    WiFi.begin(DEFAULT_SSID, DEFAULT_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected!");
        Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\nWiFi connection failed. Starting AP mode...");
        WiFi.mode(WIFI_AP);
        WiFi.softAP("ChessStream-Setup", "setup123");
        Serial.printf("AP IP: %s\n", WiFi.softAPIP().toString().c_str());
    }
}

// ============== WebSocket Setup ==============

void setupWebSocket() {
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);
    Serial.printf("WebSocket server started on port %d\n", WEBSOCKET_PORT);
}

// ============== Board Scanning ==============

void scanBoard() {
    // Scan all 64 squares
    for (int square = 0; square < NUM_SQUARES; square++) {
        uint8_t reading = readSquare(square);
        
        // Debounce logic
        if (reading != pendingState[square]) {
            pendingState[square] = reading;
            lastChangeTime[square] = millis();
        } else if (millis() - lastChangeTime[square] >= DEBOUNCE_MS) {
            // State is stable, update current board
            if (currentBoard[square] != reading) {
                previousBoard[square] = currentBoard[square];
                currentBoard[square] = reading;
            }
        }
    }
}

uint8_t readSquare(int square) {
    // Determine which MUX and channel
    int mux = square / 16;      // 0-3
    int channel = square % 16;  // 0-15
    
    // Set MUX channel (same for all MUXes)
    setMuxChannel(channel);
    
    // Small delay for MUX to settle
    delayMicroseconds(10);
    
    // Read the appropriate MUX signal pin
    int pin;
    switch (mux) {
        case 0: pin = MUX1_SIG; break;
        case 1: pin = MUX2_SIG; break;
        case 2: pin = MUX3_SIG; break;
        case 3: pin = MUX4_SIG; break;
        default: return 0;
    }
    
    // Reed switch: LOW = magnet present (piece), HIGH = no magnet (empty)
    return digitalRead(pin) == LOW ? 1 : 0;
}

void setMuxChannel(int channel) {
    // Set 4-bit channel address
    digitalWrite(SEL_A, channel & 0x01);
    digitalWrite(SEL_B, (channel >> 1) & 0x01);
    digitalWrite(SEL_C, (channel >> 2) & 0x01);
    digitalWrite(SEL_D, (channel >> 3) & 0x01);
}

// ============== Change Detection ==============

void processChanges() {
    for (int square = 0; square < NUM_SQUARES; square++) {
        if (currentBoard[square] != previousBoard[square]) {
            if (currentBoard[square] == 0) {
                // Piece lifted
                handleLift(square);
            } else {
                // Piece placed
                handlePlace(square);
            }
            previousBoard[square] = currentBoard[square];
        }
    }
}

void handleLift(int square) {
    Serial.printf("LIFT: %s\n", SQUARE_NAMES[square]);
    
    // Remember lifted square for move detection
    liftedSquare = square;
    liftTime = millis();
    
    // Broadcast lift event
    StaticJsonDocument<128> doc;
    doc["event"] = "lift";
    doc["square"] = SQUARE_NAMES[square];
    doc["board_id"] = BOARD_ID;
    doc["timestamp"] = millis();
    
    String json;
    serializeJson(doc, json);
    webSocket.broadcastTXT(json);
    
    // Blink LED
    digitalWrite(LED_PIN, HIGH);
}

void handlePlace(int square) {
    Serial.printf("PLACE: %s\n", SQUARE_NAMES[square]);
    
    // If we have a lifted piece, this completes a move
    if (liftedSquare >= 0 && liftedSquare != square) {
        broadcastMove(SQUARE_NAMES[liftedSquare], SQUARE_NAMES[square]);
        moveNumber++;
        whiteToMove = !whiteToMove;
    }
    
    // Reset lifted square
    liftedSquare = -1;
    
    // Broadcast place event
    StaticJsonDocument<128> doc;
    doc["event"] = "place";
    doc["square"] = SQUARE_NAMES[square];
    doc["board_id"] = BOARD_ID;
    doc["timestamp"] = millis();
    
    String json;
    serializeJson(doc, json);
    webSocket.broadcastTXT(json);
    
    // LED off
    digitalWrite(LED_PIN, LOW);
}

void broadcastMove(const char* from, const char* to) {
    Serial.printf("MOVE: %s -> %s (Move %d, %s)\n", 
                  from, to, moveNumber + 1, 
                  whiteToMove ? "White" : "Black");
    
    StaticJsonDocument<256> doc;
    doc["event"] = "move";
    doc["from"] = from;
    doc["to"] = to;
    doc["move_number"] = moveNumber + 1;
    doc["color"] = whiteToMove ? "white" : "black";
    doc["board_id"] = BOARD_ID;
    doc["timestamp"] = millis();
    
    // UCI format move (e.g., "e2e4")
    char uci[5];
    snprintf(uci, sizeof(uci), "%s%s", from, to);
    doc["uci"] = uci;
    
    String json;
    serializeJson(doc, json);
    webSocket.broadcastTXT(json);
}

void broadcastBoardState() {
    StaticJsonDocument<512> doc;
    doc["event"] = "board_state";
    doc["board_id"] = BOARD_ID;
    doc["move_number"] = moveNumber;
    doc["to_move"] = whiteToMove ? "white" : "black";
    
    JsonArray squares = doc.createNestedArray("occupied");
    for (int i = 0; i < NUM_SQUARES; i++) {
        if (currentBoard[i]) {
            squares.add(SQUARE_NAMES[i]);
        }
    }
    
    String json;
    serializeJson(doc, json);
    webSocket.broadcastTXT(json);
}

// ============== WebSocket Events ==============

void webSocketEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.printf("[%u] Disconnected\n", num);
            break;
            
        case WStype_CONNECTED: {
            IPAddress ip = webSocket.remoteIP(num);
            Serial.printf("[%u] Connected from %s\n", num, ip.toString().c_str());
            
            // Send welcome message
            StaticJsonDocument<256> doc;
            doc["event"] = "connected";
            doc["board_id"] = BOARD_ID;
            doc["firmware"] = FIRMWARE_VERSION;
            doc["message"] = "ChessStream India - Ready";
            
            String json;
            serializeJson(doc, json);
            webSocket.sendTXT(num, json);
            
            // Send current board state
            broadcastBoardState();
            break;
        }
        
        case WStype_TEXT: {
            Serial.printf("[%u] Received: %s\n", num, payload);
            
            // Parse command
            StaticJsonDocument<256> doc;
            DeserializationError error = deserializeJson(doc, payload);
            
            if (!error) {
                const char* cmd = doc["cmd"];
                
                if (strcmp(cmd, "get_state") == 0) {
                    broadcastBoardState();
                } else if (strcmp(cmd, "new_game") == 0) {
                    moveNumber = 0;
                    whiteToMove = true;
                    gameInProgress = true;
                    Serial.println("New game started");
                } else if (strcmp(cmd, "reset") == 0) {
                    moveNumber = 0;
                    whiteToMove = true;
                    gameInProgress = false;
                    liftedSquare = -1;
                    Serial.println("Board reset");
                }
            }
            break;
        }
        
        default:
            break;
    }
}

// ============== Utilities ==============

void blinkLED(int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(delayMs);
        digitalWrite(LED_PIN, LOW);
        delay(delayMs);
    }
}
