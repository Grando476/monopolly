import socket
import threading
import sys
import json
import os

HOST = '172.20.10.3'
#HOST = '25.36.22.142'
#HOST = '127.0.0.1
PORT = 65432

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_cell(space_idx, state, width=14):
    """
    Formats a single square cell representing a space on the board.
    Takes a width, centers the name of the cell, and puts pawns of any players currently on it.
    """
    board = state.get("board", [])
    if space_idx < 0 or space_idx >= len(board):
        return " " * width

    space = board[space_idx]
    
    pawn_str = ""
    for p in state.get("players", []):
        if p["position"] == space_idx:
            pawn_str += f"[{p['id']}]"
            
    header = space["short_name"].center(width)
    
    # Ownership or Price info
    info = ""
    if space["space_type"] == "PROPERTY":
        if space["owner"]:
            info = f"Own: {space['owner'][:5]}".center(width)
        else:
            info = f"${space['price']}".center(width)
    elif space["space_type"] == "TAX":
        info = f"-${space['price']}".center(width)
        
    pawns = pawn_str.center(width)
    
    cell_lines = [
        header,
        info if info else " "*width,
        pawns if pawns else " "*width
    ]
    return cell_lines

def draw_tui(state):
    clear_screen()
    
    print("="*76)
    print(" "*33 + "MONOPOLY" + " "*35)
    print("="*76)
    
    # Top Row (Index 0 to 4)
    top_row = [format_cell(i, state) for i in range(5)]
    
    # Middle Rows
    mid_row1 = [format_cell(15, state), [" "*14]*3, [" "*14]*3, [" "*14]*3, format_cell(5, state)]
    mid_row2 = [format_cell(14, state), [" "*14]*3, [" "*14]*3, [" "*14]*3, format_cell(6, state)]
    mid_row3 = [format_cell(13, state), [" "*14]*3, [" "*14]*3, [" "*14]*3, format_cell(7, state)]
    
    # Bottom Row (Index 12 down to 8)
    bottom_row = [format_cell(12, state), format_cell(11, state), format_cell(10, state), format_cell(9, state), format_cell(8, state)]
    
    def print_row(row_cells):
        print("-" * 76)
        for line_idx in range(3):
            line = "|"
            for cell in row_cells:
                # cell is a list of 3 strings
                line += cell[line_idx] + "|"
            print(line)
            
    print_row(top_row)
    print_row(mid_row1)
    print_row(mid_row2)
    print_row(mid_row3)
    print_row(bottom_row)
    print("-" * 76)
    
    # Print Player Stats
    print("\n[ PLAYERS ]")
    for p in state.get("players", []):
        status = "(JAIL)" if p["in_jail"] else ""
        print(f"[{p['id']}] {p['name']:10} | ${p['balance']:4} | Props: {len(p['inventory']):2} {status}")
        
    print("-" * 76)
    # Print Message Log
    print("\n[ ACTIVITY ]")
    for msg in state.get("messages", []):
        print(f"> {msg}")
        
    print("=" * 76)
    
    prompt = state.get("prompt", "")
    if prompt:
        # Prompt needs to cleanly exit line buffer
        sys.stdout.write(f"\n{prompt}")
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
