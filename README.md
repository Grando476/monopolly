# Console Monopoly

## Brief Description of the Game
Console Monopoly is a terminal-based multiplayer iteration of the classic Monopoly game. Designed for a minimalist 16-space board, the game allows players to move their pawns, purchase properties (featuring custom names such as "Zein Kebab", "Zabka", "Lidl", etc.), pay rent to other players, get sent to jail, and pay taxes. It features a colorful text-based user interface (TUI) utilizing ANSI escape codes for a vibrant command-line experience. The game is fully networked, supporting multiple players connecting over a local network, complete with session persistence across individual terminals.

## Project File Structure
The project is split into a classic Client-Server architecture:
- `server.py`: The authoritative game server. It handles incoming client connections, manages the overall game state (the board, player balances, inventory, turn loops), and broadcasts updates to connected clients using a JSON-based protocol. It also includes a small Tkinter GUI for quick server administration (e.g., shutting down the server safely).
- `client.py`: The user-facing client application. Players run this script to connect to the game server. It listens for state updates from the server and handles the rendering of the ANSI-colored text user interface. It also captures and transmits player inputs back to the server.
- `assets/`: Directory containing project images and screenshots.

## Concurrent Programming Methods Used
This project heavily relies on multithreading to manage networked multiplayer functionality efficiently:
- **`threading.Thread`**: Used extensively in both the server and the client.
  - The server spawns a daemon thread (`accept_clients`) to asynchronously accept incoming client connections.
  - Each connected client gets its own dedicated handler thread (`handle_client`) so that slower clients don't block the server.
  - The main Monopoly game loop runs concurrently in its own thread (`game_loop`).
  - The client runs a background daemon thread (`receive_messages`) to constantly listen for and render broadcasted game updates without interrupting the user's input prompt.
- **`threading.Lock`**: The server utilizes a mutex lock (`game.lock`) to protect critical sections of code. This ensures thread safety when modifying shared game state, such as appending new players to the lobby or validating authentication tokens during reconnections, preventing race conditions.
- **`queue.Queue`**: Thread-safe queues are used for handling user input gracefully on the server side (`player.input_queue`). The network threads push received commands into a player's queue, while the game loop thread polls this queue with a timeout. This prevents the main game loop from blocking indefinitely if a player takes too long to respond or disconnects abruptly.

## External Libraries and Frameworks
This project is built using only Python's standard libraries, ensuring it is lightweight and requires no external `pip` dependencies:
- `socket`: For underlying TCP/IP network communication.
- `threading` & `queue`: For concurrent thread management and thread-safe data exchange.
- `json`: For structuring, serializing, and deserializing the game state sent over the network.
- `tkinter`: Used for creating a minimal graphical user interface for the Server Admin panel.
- `uuid`: To generate unique, unguessable authentication tokens for player session management.
- `os`, `sys`, `time`, `random`: Standard utilities for OS interaction, timing, and random number generation (dice rolls).

## Screenshots
### Console Client Gameplay
![Console Gameplay](assets/gameplay.png)

### Server Administration GUI
![Server Admin](assets/server_admin.png)
