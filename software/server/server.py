"""
ChessStream India - Streaming Server

Connects to ChessStream boards and broadcasts games to various platforms.

License: MIT
Author: Monara Ventures (Poorav Kadiyan)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import websockets
from aiohttp import web
import chess
import chess.pgn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ChessStream')

# ============== Configuration ==============

CONFIG = {
    'server_host': '0.0.0.0',
    'server_port': 8080,
    'board_port': 81,  # Port boards broadcast on
    'pgn_dir': './games',
    'auto_save_pgn': True,
}

# ============== Data Classes ==============

class ChessBoard:
    """Represents a connected ChessStream board."""
    
    def __init__(self, board_id: str, ip: str):
        self.board_id = board_id
        self.ip = ip
        self.connected = False
        self.websocket = None
        self.game: Optional[chess.Board] = None
        self.pgn_game: Optional[chess.pgn.Game] = None
        self.move_node = None
        self.white_player = "White"
        self.black_player = "Black"
        self.event_name = "ChessStream Game"
        self.last_seen = None
    
    def start_game(self, white: str = "White", black: str = "Black", event: str = "ChessStream Game"):
        """Start a new game on this board."""
        self.game = chess.Board()
        self.pgn_game = chess.pgn.Game()
        self.pgn_game.headers["Event"] = event
        self.pgn_game.headers["Site"] = "ChessStream India"
        self.pgn_game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        self.pgn_game.headers["White"] = white
        self.pgn_game.headers["Black"] = black
        self.white_player = white
        self.black_player = black
        self.event_name = event
        self.move_node = self.pgn_game
        logger.info(f"Game started on {self.board_id}: {white} vs {black}")
    
    def add_move(self, uci_move: str) -> bool:
        """Add a move to the current game."""
        if not self.game:
            return False
        
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.game.legal_moves:
                self.game.push(move)
                self.move_node = self.move_node.add_variation(move)
                logger.info(f"Move on {self.board_id}: {uci_move}")
                return True
            else:
                logger.warning(f"Illegal move on {self.board_id}: {uci_move}")
                return False
        except Exception as e:
            logger.error(f"Error adding move: {e}")
            return False
    
    def end_game(self, result: str = "*") -> str:
        """End the current game and return PGN."""
        if not self.pgn_game:
            return ""
        
        self.pgn_game.headers["Result"] = result
        pgn_str = str(self.pgn_game)
        
        # Save to file if enabled
        if CONFIG['auto_save_pgn']:
            self._save_pgn(pgn_str)
        
        logger.info(f"Game ended on {self.board_id}: {result}")
        return pgn_str
    
    def _save_pgn(self, pgn_str: str):
        """Save PGN to file."""
        pgn_dir = Path(CONFIG['pgn_dir'])
        pgn_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.board_id}_{timestamp}.pgn"
        filepath = pgn_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(pgn_str)
        
        logger.info(f"PGN saved: {filepath}")


class ChessStreamServer:
    """Main server managing boards and clients."""
    
    def __init__(self):
        self.boards: Dict[str, ChessBoard] = {}
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/boards', self.handle_list_boards)
        self.app.router.add_get('/api/boards/{board_id}/state', self.handle_board_state)
        self.app.router.add_get('/api/games', self.handle_list_games)
        self.app.router.add_get('/ws', self.handle_websocket)
    
    async def handle_index(self, request):
        """Serve the web dashboard."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ChessStream India</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
                h1 { color: #e94560; }
                .board-card { background: #16213e; padding: 15px; margin: 10px 0; border-radius: 8px; }
                .connected { border-left: 4px solid #4ecca3; }
                .disconnected { border-left: 4px solid #e94560; }
                .move-list { font-family: monospace; background: #0f0f23; padding: 10px; border-radius: 4px; }
            </style>
        </head>
        <body>
            <h1>♟️ ChessStream India</h1>
            <p>Low-cost tournament streaming</p>
            <div id="boards"></div>
            <script>
                const ws = new WebSocket(`ws://${location.host}/ws`);
                ws.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    console.log('Event:', data);
                    // Update UI based on events
                };
                
                // Fetch boards
                fetch('/api/boards')
                    .then(r => r.json())
                    .then(boards => {
                        const container = document.getElementById('boards');
                        boards.forEach(b => {
                            container.innerHTML += `
                                <div class="board-card ${b.connected ? 'connected' : 'disconnected'}">
                                    <h3>${b.board_id}</h3>
                                    <p>IP: ${b.ip}</p>
                                    <p>Status: ${b.connected ? '🟢 Connected' : '🔴 Disconnected'}</p>
                                </div>
                            `;
                        });
                    });
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def handle_list_boards(self, request):
        """List all boards."""
        boards = [
            {
                'board_id': b.board_id,
                'ip': b.ip,
                'connected': b.connected,
                'last_seen': b.last_seen.isoformat() if b.last_seen else None,
            }
            for b in self.boards.values()
        ]
        return web.json_response(boards)
    
    async def handle_board_state(self, request):
        """Get state of a specific board."""
        board_id = request.match_info['board_id']
        board = self.boards.get(board_id)
        
        if not board:
            return web.json_response({'error': 'Board not found'}, status=404)
        
        state = {
            'board_id': board.board_id,
            'connected': board.connected,
            'game_in_progress': board.game is not None,
            'fen': board.game.fen() if board.game else None,
            'white': board.white_player,
            'black': board.black_player,
        }
        return web.json_response(state)
    
    async def handle_list_games(self, request):
        """List saved games."""
        pgn_dir = Path(CONFIG['pgn_dir'])
        if not pgn_dir.exists():
            return web.json_response([])
        
        games = []
        for pgn_file in pgn_dir.glob('*.pgn'):
            games.append({
                'filename': pgn_file.name,
                'size': pgn_file.stat().st_size,
                'modified': datetime.fromtimestamp(pgn_file.stat().st_mtime).isoformat(),
            })
        
        return web.json_response(sorted(games, key=lambda x: x['modified'], reverse=True))
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections from clients."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.append(ws)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._handle_client_message(ws, msg.data)
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.clients.remove(ws)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
        
        return ws
    
    async def _handle_client_message(self, ws, data: str):
        """Handle message from a client."""
        try:
            msg = json.loads(data)
            cmd = msg.get('cmd')
            board_id = msg.get('board')
            
            if cmd == 'start_game' and board_id:
                board = self.boards.get(board_id)
                if board:
                    board.start_game(
                        white=msg.get('white', 'White'),
                        black=msg.get('black', 'Black'),
                        event=msg.get('event', 'ChessStream Game')
                    )
                    await self._broadcast({
                        'event': 'game_started',
                        'board': board_id,
                        'white': board.white_player,
                        'black': board.black_player,
                    })
            
            elif cmd == 'end_game' and board_id:
                board = self.boards.get(board_id)
                if board:
                    result = msg.get('result', '*')
                    pgn = board.end_game(result)
                    await self._broadcast({
                        'event': 'game_ended',
                        'board': board_id,
                        'result': result,
                        'pgn': pgn,
                    })
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client: {data}")
    
    async def _broadcast(self, data: dict):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        
        message = json.dumps(data)
        await asyncio.gather(
            *[client.send_str(message) for client in self.clients if not client.closed],
            return_exceptions=True
        )
    
    async def connect_to_board(self, ip: str, port: int = 81):
        """Connect to a ChessStream board."""
        uri = f"ws://{ip}:{port}"
        
        try:
            async with websockets.connect(uri) as ws:
                # Wait for welcome message
                welcome = await ws.recv()
                data = json.loads(welcome)
                
                board_id = data.get('board_id', f'board_{ip}')
                board = ChessBoard(board_id, ip)
                board.connected = True
                board.websocket = ws
                board.last_seen = datetime.now()
                self.boards[board_id] = board
                
                logger.info(f"Connected to board: {board_id} at {ip}")
                await self._broadcast({'event': 'board_connected', 'board': board_id})
                
                # Listen for events from board
                async for message in ws:
                    await self._handle_board_message(board, message)
        
        except Exception as e:
            logger.error(f"Error connecting to board at {ip}: {e}")
    
    async def _handle_board_message(self, board: ChessBoard, message: str):
        """Handle message from a board."""
        try:
            data = json.loads(message)
            event = data.get('event')
            board.last_seen = datetime.now()
            
            if event == 'move':
                uci = data.get('uci')
                if uci and board.add_move(uci):
                    await self._broadcast({
                        'event': 'move',
                        'board': board.board_id,
                        'from': data.get('from'),
                        'to': data.get('to'),
                        'uci': uci,
                        'fen': board.game.fen() if board.game else None,
                    })
            
            elif event == 'lift':
                await self._broadcast({
                    'event': 'lift',
                    'board': board.board_id,
                    'square': data.get('square'),
                })
            
            elif event == 'place':
                await self._broadcast({
                    'event': 'place',
                    'board': board.board_id,
                    'square': data.get('square'),
                })
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from board: {message}")
    
    async def run(self):
        """Run the server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            CONFIG['server_host'],
            CONFIG['server_port']
        )
        await site.start()
        
        logger.info(f"Server running at http://{CONFIG['server_host']}:{CONFIG['server_port']}")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


# ============== Main ==============

async def main():
    """Main entry point."""
    server = ChessStreamServer()
    
    # Example: Connect to a board (uncomment and set IP)
    # asyncio.create_task(server.connect_to_board('192.168.1.100'))
    
    await server.run()


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════╗
    ║     ChessStream India Server          ║
    ║     Low-cost tournament streaming     ║
    ╚═══════════════════════════════════════╝
    """)
    
    asyncio.run(main())
