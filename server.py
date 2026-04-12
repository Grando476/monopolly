import socket
import threading
import queue
import random
import time
import json
import os
import tkinter as tk

HOST = '25.36.22.142'
#HOST = '127.0.0.1'
PORT = 65432

class Space:
    def __init__(self, name, space_type, price=0, rent=0, short_name=""):
        self.name = name
        self.short_name = short_name if short_name else name[:10]
        self.space_type = space_type # "GO", "PROPERTY", "TAX", "JAIL", "GO_TO_JAIL", "FREE_PARKING"
        self.price = price
        self.rent = rent
        self.owner = None
        
    def to_dict(self):
        return {
            "name": self.name,
            "short_name": self.short_name,
            "space_type": self.space_type,
            "price": self.price,
            "rent": self.rent,
            "owner": self.owner.name if self.owner else None
        }

class Player:
    def __init__(self, conn, addr, p_id):
        self.conn = conn
        self.addr = addr
        self.id = p_id # 1-indexed to act as pawn number like [1]
        self.name = None
        self.balance = 1500
        self.position = 0
        self.inventory = []
        self.in_jail = False
        self.jail_turns = 0
        self.active = True
        self.input_queue = queue.Queue()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "balance": self.balance,
            "position": self.position,
            "in_jail": self.in_jail,
            "active": self.active,
            "inventory": [space.name for space in self.inventory]
        }

    def send_raw(self, msg):
        try:
            self.conn.sendall((msg + "\n").encode())
        except Exception:
            self.active = False
            
    def dump_queue(self):
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break

    def recv(self, timeout=86400):
        self.dump_queue()
        try:
            return self.input_queue.get(timeout=timeout)
        except Exception:
            self.active = False
            return ""

class MonopolyGame:
    def __init__(self):
        self.players = []
        self.board = self.init_board()
        self.lock = threading.Lock()
        self.started = False
        self.message_log = []

    def init_board(self):
        # 16 space minimalist square board logic
        return [
            Space("GO", "GO", short_name="GO"),
            Space("Zein Kebab", "PROPERTY", 60, 10, "Zein"),
            Space("Zabka", "PROPERTY", 80, 15, "Zabka"),
            Space("Income Tax", "TAX", 300, short_name="Tax"),
            Space("Jail / Visit", "JAIL", short_name="Jail"),
            Space("Dziekanat", "PROPERTY", 100, 25, "Dziekanat"),
            Space("Gmach Glowny B", "PROPERTY", 120, 80, "GG B"),
            Space("Gmach Glowny ", "PROPERTY", 140, 90, "GG"),
            Space("Free Park", "FREE_PARKING", short_name="Free Prk"),
            Space("WZiE", "PROPERTY", 200, 30, "ZiE"),
            Space("Old WETI", "PROPERTY", 240, 40, "Old ETI"),
            Space("New WETI", "PROPERTY", 260, 50, "New ETI"),
            Space("Go To Jail!", "GO_TO_JAIL", short_name="Go 2 Jail"),
            Space("DS2", "PROPERTY", 280, 100, "DS2"),
            Space("DS7", "PROPERTY", 350, 120, "DS7"),
            Space("DS5", "PROPERTY", 400, 150, "DS5")
        ]

    def log(self, msg):
        print(msg)
        self.message_log.append(msg)
        # Keep log trim
        if len(self.message_log) > 10:
            self.message_log.pop(0)

    def broadcast_state(self, prompt="", target_player=None):
        """
        Sends the entire game state as JSON to all players.
        If target_player is specified, only that player gets the prompt.
        """
        state = {
            "board": [s.to_dict() for s in self.board],
            "players": [p.to_dict() for p in self.players if p.active],
            "messages": self.message_log,
            "started": self.started,
            "prompt": ""
        }
        
        for p in self.players:
            if p.active:
                if target_player and p == target_player:
                    state["prompt"] = prompt
                elif not target_player:
                    state["prompt"] = prompt
                else:
                    state["prompt"] = ""
                    
                payload = json.dumps(state)
                # To distinguish json payloads from standard text prompts (like login),
                # we'll prefix them with JSON_DATA|
                p.send_raw("JSON_DATA|" + payload)

    def game_loop(self):
        self.log("!!! THE GAME IS STARTING !!!")
        self.broadcast_state()
        time.sleep(1)
        turn_idx = 0
        
        while True:
            active_players = [p for p in self.players if p.active]
            if len(active_players) < 2 and len(self.players) > 1:
                self.log("Game over - Not enough players remaining")
                self.broadcast_state()
                break
                
            player = self.players[turn_idx % len(self.players)]
            if not player.active:
                turn_idx += 1
                continue
                
            self.log(f"---> Turn of {player.name} <---")
            self.broadcast_state()
            
            # 1. Jail Logic
            if player.in_jail:
                player.jail_turns += 1
                self.log(f"{player.name} is in jail - Turn {player.jail_turns}.")
                
                self.broadcast_state(prompt="You can pay $50 to get out [Write (y/n) or press Enter to roll] ", target_player=player)
                ans = player.recv().lower()
                
                if ans == 'y':
                    if player.balance >= 50:
                        player.balance -= 50
                        player.in_jail = False
                        player.jail_turns = 0
                        self.log(f"{player.name} paid $50 and is out of jail.")
                    else:
                        self.log("Not enough money. You must roll")
                
                if player.in_jail and player.jail_turns >= 3:
                    self.log(f"{player.name} must pay $50 to get out of jail.")
                    player.balance -= 50
                    player.in_jail = False
                    player.jail_turns = 0
                
                if player.in_jail:
                    self.broadcast_state(prompt="Press Enter to roll for doubles...", target_player=player)
                    player.recv()
                    
                    d1, d2 = random.randint(1, 6), random.randint(1, 6)
                    self.log(f"{player.name} rolled {d1} and {d2}.")
                    if d1 == d2:
                        self.log(f"{player.name} successfully rolled doubles and is out of jail")
                        player.in_jail = False
                        player.jail_turns = 0
                        self.move_player(player, d1 + d2)
                    else:
                        self.log(f"{player.name} stays in jail.")
                    
                    self.broadcast_state()
                    turn_idx += 1
                    time.sleep(1.5)
                    continue

            # 2. Regular Turn Logic
            self.broadcast_state(prompt="Press Enter to roll the dice...", target_player=player)
            player.recv()
            if not player.active:
                turn_idx += 1
                continue
                
            d1, d2 = random.randint(1, 6), random.randint(1, 6)
            self.log(f"{player.name} rolled {d1} and {d2} -> Total: {d1+d2}")
            self.move_player(player, d1 + d2)
            
            # Simple simulation of rolling doubles (doesn't grant an extra turn yet)
            self.broadcast_state()
            turn_idx += 1
            time.sleep(1.5)

    def move_player(self, player, steps):
        old_pos = player.position
        
        # Animate pawn moving one space at a time
        for _ in range(steps):
            player.position = (player.position + 1) % len(self.board)
            self.broadcast_state()
            time.sleep(0.3)
        
        if player.position < old_pos:
            self.log(f"{player.name} passed start and collected $200!")
            player.balance += 200
            
        space = self.board[player.position]
        self.log(f"{player.name} landed on [{space.name}].")
        self.broadcast_state()
        time.sleep(0.5)
        
        if space.space_type == "PROPERTY":
            if space.owner is None:
                if player.balance >= space.price:
                    self.broadcast_state(prompt=f"Buy {space.name} for ${space.price}? (y/n): ", target_player=player)
                    ans = player.recv().lower()
                    
                    if ans == 'y':
                        player.balance -= space.price
                        space.owner = player
                        player.inventory.append(space)
                        self.log(f"{player.name} bought {space.name}!")
                    else:
                        self.log(f"{player.name} chose not to buy.")
                else:
                    self.log(f"{player.name} doesn't have enough money to buy {space.name}.")
            elif space.owner != player:
                rent = space.rent
                owner_name = space.owner.name
                self.log(f"{player.name} must pay ${rent} rent to {owner_name}!")
                player.balance -= rent
                space.owner.balance += rent
                if player.balance < 0:
                    self.log(f"{player.name} went bankrupt")
                    player.active = False
                    
        elif space.space_type == "TAX":
            self.log(f"{player.name} paid $200 in taxes")
            player.balance -= 200
            if player.balance < 0:
                self.log(f"{player.name} went bankrupt")
                player.active = False
                
        elif space.space_type == "GO_TO_JAIL":
            self.log(f"{player.name} goes to Jail")
            self.broadcast_state()
            time.sleep(1)
            player.position = 4  # Index of Jail
            player.in_jail = True
            
        self.broadcast_state()


def handle_client(conn, addr, game):
    conn.sendall(b"Welcome to Console Monopoly!\nEnter your name: ")
    try:
        name = conn.recv(1024).decode().strip()
    except Exception:
        conn.close()
        return
        
    with game.lock:
        p_id = len(game.players) + 1
        player = Player(conn, addr, p_id)
        player.name = name if name else f"Player_{addr[1]}"
        game.players.append(player)
        num_players = len(game.players)
    
    game.log(f"[+] {player.name} joined the game! ({num_players} players in lobby)")
    
    if num_players >= 2 and not game.started:
        game.broadcast_state(prompt=">>> We have 2+ players! Type 'start' to begin the game. <<<")
    else:
        game.broadcast_state(prompt="Waiting for more players to join...")

    # Main Client Listener Loop
    while player.active:
        try:
            data = conn.recv(1024).decode().strip()
            if not data and not data == "":
                player.active = False
                break
                
            if not game.started:
                if data.lower() == 'start' and len([p for p in game.players if p.active]) >= 2:
                    with game.lock:
                        if not game.started:
                            game.started = True
                            threading.Thread(target=game.game_loop, daemon=True).start()
            else:
                player.input_queue.put(data)
                
        except Exception:
            player.active = False
            game.log(f"[-] {player.name} disconnected.")
            game.broadcast_state()
            break
            
    conn.close()


def accept_clients(server, game):
    try:
        while True:
            conn, addr = server.accept()
            print(f"Connection from {addr}")
            threading.Thread(target=handle_client, args=(conn, addr, game), daemon=True).start()
    except Exception:
        pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
    except Exception as e:
        print(f"Failed to bind on {HOST}:{PORT} - {e}")
        return
        
    server.listen()
    print(f"Monopoly Server listening on {HOST}:{PORT}")
    
    game = MonopolyGame()
    
    accept_thread = threading.Thread(target=accept_clients, args=(server, game), daemon=True)
    accept_thread.start()
    
    root = tk.Tk()
    root.title("Server Admin")
    root.geometry("250x120")
    
    tk.Label(root, text=f"Server running on\n{HOST}:{PORT}", font=("Helvetica", 12)).pack(pady=10)
    
    def on_shutdown():
        print("\nShutting down server via UI...")
        game.log("SERVER IS SHUTTING DOWN!")
        game.broadcast_state()
        time.sleep(0.5)
        server.close()
        root.destroy()
        os._exit(0)
        
    tk.Button(root, text="Shutdown Server", command=on_shutdown, bg="red", fg="white", font=("Helvetica", 10, "bold")).pack(pady=5)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        on_shutdown()

if __name__ == '__main__':
    main()
