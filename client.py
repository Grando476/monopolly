import socket
import threading
import sys
import json
import os

#HOST = '172.20.10.3'
#HOST = '25.36.22.142'
HOST = '127.0.0.1'
PORT = 65432

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ANSI Color Codes
COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
}

PLAYER_COLORS = [COLORS["BLUE"], COLORS["MAGENTA"], COLORS["YELLOW"], COLORS["CYAN"], COLORS["RED"], COLORS["GREEN"]]

def center_with_ansi(text_with_ansi, plain_text_len, width):
    padding = width - plain_text_len
    if padding <= 0:
        return text_with_ansi
    left = padding // 2
    right = padding - left
    return (" " * left) + text_with_ansi + (" " * right)

def format_cell(space_idx, state, width=14):
    """
    Formats a single square cell representing a space on the board.
    Takes a width, centers the name of the cell, and puts pawns of any players currently on it.
    """
    board = state.get("board", [])
    if space_idx < 0 or space_idx >= len(board):
        return [" " * width] * 3

    space = board[space_idx]
    
    pawn_str = ""
    pawn_len = 0
    for i, p in enumerate(state.get("players", [])):
        if p["position"] == space_idx:
            c = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            pawn_str += f"{c}[{p['id']}]{COLORS['RESET']}"
            pawn_len += len(str(p['id'])) + 2
            
    color_prefix = COLORS["WHITE"]
    if space["space_type"] == "PROPERTY":
        color_prefix = COLORS["WHITE"]
    elif space["space_type"] == "TAX":
        color_prefix = COLORS["RED"]
    elif space["space_type"] == "JAIL":
        color_prefix = COLORS["YELLOW"]
    elif space["space_type"] == "GO":
        color_prefix = COLORS["GREEN"] + COLORS["BOLD"]
        
    header_text = space["short_name"]
    header = f"{color_prefix}{header_text}{COLORS['RESET']}"
    header_padded = center_with_ansi(header, len(header_text), width)
    
    # Ownership or Price info
    info_text = ""
    info = ""
    if space["space_type"] == "PROPERTY":
        if space.get("owner"):
            info_text = f"Own: {space['owner'][:5]}"
            owner_idx = next((i for i, p in enumerate(state.get("players", [])) if p["id"] == space["owner"]), 0)
            c = PLAYER_COLORS[owner_idx % len(PLAYER_COLORS)]
            info = f"{c}{info_text}{COLORS['RESET']}"
        else:
            info_text = f"${space['price']}"
            info = f"{COLORS['GREEN']}{info_text}{COLORS['RESET']}"
    elif space["space_type"] == "TAX":
        info_text = f"-${space['price']}"
        info = f"{COLORS['RED']}{info_text}{COLORS['RESET']}"
        
    info_padded = center_with_ansi(info, len(info_text), width) if info_text else " "*width
    pawns_padded = center_with_ansi(pawn_str, pawn_len, width) if pawn_len > 0 else " "*width
    
    cell_lines = [
        header_padded,
        info_padded,
        pawns_padded
    ]
    return cell_lines

def draw_tui(state):
    clear_screen()
    
    print(f"{COLORS['CYAN']}="*76 + COLORS['RESET'])
    print(f"{COLORS['YELLOW']}{COLORS['BOLD']}" + " "*33 + "MONOPOLY" + " "*35 + COLORS['RESET'])
    print(f"{COLORS['CYAN']}="*76 + COLORS['RESET'])
    
    # Top Row (Index 0 to 4)
    top_row = [format_cell(i, state) for i in range(5)]
    
    # Middle Rows
    mid_row1 = [format_cell(15, state), [" "*14]*3, [" "*14]*3, [" "*14]*3, format_cell(5, state)]
    mid_row2 = [format_cell(14, state), [" "*14]*3, [" "*14]*3, [" "*14]*3, format_cell(6, state)]
    mid_row3 = [format_cell(13, state), [" "*14]*3, [" "*14]*3, [" "*14]*3, format_cell(7, state)]
    
    # Bottom Row (Index 12 down to 8)
    bottom_row = [format_cell(12, state), format_cell(11, state), format_cell(10, state), format_cell(9, state), format_cell(8, state)]
    
    def print_row(row_cells):
        print(f"{COLORS['CYAN']}-" * 76 + COLORS['RESET'])
        for line_idx in range(3):
            line = f"{COLORS['CYAN']}|{COLORS['RESET']}"
            for cell in row_cells:
                # cell is a list of 3 strings
                line += cell[line_idx] + f"{COLORS['CYAN']}|{COLORS['RESET']}"
            print(line)
            
    print_row(top_row)
    print_row(mid_row1)
    print_row(mid_row2)
    print_row(mid_row3)
    print_row(bottom_row)
    print(f"{COLORS['CYAN']}-" * 76 + COLORS['RESET'])
    
    # Print Player Stats
    print(f"\n{COLORS['BOLD']}[ PLAYERS ]{COLORS['RESET']}")
    for i, p in enumerate(state.get("players", [])):
        c = PLAYER_COLORS[i % len(PLAYER_COLORS)]
        status = f"{COLORS['RED']}(JAIL){COLORS['RESET']}" if p.get("in_jail") else ""
        print(f"{c}[{p['id']}]{COLORS['RESET']} {p['name']:10} | {COLORS['GREEN']}${p['balance']:4}{COLORS['RESET']} | Props: {len(p['inventory']):2} {status}")
        
    print(f"{COLORS['CYAN']}-" * 76 + COLORS['RESET'])
    # Print Message Log
    print(f"\n{COLORS['BOLD']}[ ACTIVITY ]{COLORS['RESET']}")
    for msg in state.get("messages", []):
        print(f"{COLORS['CYAN']}>{COLORS['RESET']} {msg}")
        
    print(f"{COLORS['CYAN']}=" * 76 + COLORS['RESET'])
    
    prompt = state.get("prompt", "")
    if prompt:
        # Prompt needs to cleanly exit line buffer
        sys.stdout.write(f"\n{COLORS['YELLOW']}{prompt}{COLORS['RESET']}")
        sys.stdout.flush()


def receive_messages(sock):
    buffer = ""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("\nServer closed the connection.")
                break
                
            buffer += data.decode()
            
            # The server groups messages per line with "\n" at the end.
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                
                if line.startswith("JSON_DATA|"):
                    json_str = line.split("|", 1)[1]
                    try:
                        state = json.loads(json_str)
                        draw_tui(state)
                    except json.JSONDecodeError:
                        pass
                else:
                    # Regular text messages (like welcome prompt)
                    sys.stdout.write(line + "\n")
                    sys.stdout.flush()
                    
        except Exception as e:
            # Silently exit background thread on quit
            break
            
    sock.close()
    import os
    os._exit(0)

def main():
    if os.name == 'nt':
        os.system("")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(f"Could not connect to the Monopoly server at {HOST}:{PORT}.")
        print("Make sure 'server.py' is running!")
        return

    recv_thread = threading.Thread(target=receive_messages, args=(client,), daemon=True)
    recv_thread.start()

    try:
        while True:
            msg = sys.stdin.readline()
            if not msg:
                break
                
            client.sendall(msg.encode())
    except KeyboardInterrupt:
        print("\nExiting Monopoly...")
    finally:
        client.close()

if __name__ == '__main__':
    main()
