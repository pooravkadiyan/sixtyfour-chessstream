# ChessStream India - Streaming Server

A Python-based relay server that connects to ChessStream boards and broadcasts games to various platforms.

## Features

- Connect to multiple ChessStream boards via WebSocket
- Real-time move broadcasting
- PGN game recording
- Lichess Board API integration
- Web dashboard for monitoring

## Installation

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Start the server
python server.py

# With custom port
python server.py --port 8080

# Connect to specific board
python server.py --board 192.168.1.100
```

## Configuration

Edit `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8080

boards:
  - id: CS001
    ip: 192.168.1.100
    name: "Board 1"

lichess:
  enabled: true
  token: "your_lichess_token"

output:
  pgn_dir: "./games"
  auto_save: true
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/api/boards` | GET | List connected boards |
| `/api/boards/{id}/state` | GET | Get board state |
| `/api/games` | GET | List recorded games |
| `/api/games/{id}/pgn` | GET | Download PGN |
| `/ws` | WebSocket | Real-time updates |

## WebSocket Events

### From Server

```json
{"event": "move", "board": "CS001", "from": "e2", "to": "e4", "uci": "e2e4"}
{"event": "board_connected", "board": "CS001"}
{"event": "board_disconnected", "board": "CS001"}
{"event": "game_started", "board": "CS001", "white": "Player 1", "black": "Player 2"}
{"event": "game_ended", "board": "CS001", "result": "1-0", "pgn": "..."}
```

### To Server

```json
{"cmd": "start_game", "board": "CS001", "white": "Player 1", "black": "Player 2"}
{"cmd": "end_game", "board": "CS001", "result": "1-0"}
{"cmd": "set_clock", "board": "CS001", "white_time": 600, "black_time": 600}
```

## License

MIT License - Monara Ventures
