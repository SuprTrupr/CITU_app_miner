import os
import subprocess
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import queue
import json
import time
import requests
import re


def set_java_home(queue):
    possible_paths = [
        "C:\\Program Files\\Java",
        "C:\\Program Files (x86)\\Java"
    ]

    queue.put("Searching for Java installations...")

    for path in possible_paths:
        if os.path.exists(path):
            queue.put(f"Checking path: {path}")
            java_versions = sorted(os.listdir(path), reverse=True)  # Seřadí verze sestupně
            if java_versions:
                java_home = os.path.join(path, java_versions[0])  # Vybere nejnovější
                os.environ['JAVA_HOME'] = java_home
                queue.put(f"JAVA_HOME set to: {java_home}")
                return java_home
            else:
                queue.put(f"No Java versions found in {path}")
        else:
            queue.put(f"Path does not exist: {path}")

    queue.put("Error: Java installation not found.")
    return None


def perform_http_post_form(url, data):
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def perform_http_get(url):
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def process_staking(miner, dollar, password):
    url = "http://localhost:8082/staking"
    data = {
        "miner": miner,
        "dollar": dollar,
        "password": password
    }
    threading.Thread(target=perform_http_post_form, args=(url, data)).start()


def process_unstaking(miner, dollar, password):
    url = "http://localhost:8082/unstaking"
    data = {
        "miner": miner,
        "dollar": dollar,
        "password": password
    }
    threading.Thread(target=perform_http_post_form, args=(url, data)).start()


def fetch_nodes():
    url = "http://194.87.236.238:82/getNodes"
    try:
        response = requests.get(url)
        nodes = response.json()
        return nodes
    except Exception as e:
        return {"error": str(e)}


class Application(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Welcome to the future with CITU")
        self.configure(bg='lightblue')

        self.wallet_address_history = []
        self.difficulty_history = []

        style = ttk.Style()
        style.configure('TNotebook', background='lightblue')
        style.configure('TFrame', background='lightblue')
        style.configure('TButton', background='lightgrey')

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.create_info_tab()
        self.create_wallet_tab()
        self.create_mining_tab()
        self.create_staking_tab()
        self.create_send_coin_tab()
        self.create_create_account_tab()

        bottom_frame = tk.Frame(self, bg='lightblue')
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.console = scrolledtext.ScrolledText(bottom_frame, wrap=tk.WORD, height=35, width=100, bg='black',
                                                 fg='white')
        self.console.pack(fill=tk.BOTH, expand=True)

        self.queue = queue.Queue()
        self.queue_lock = threading.Lock()
        self.output_buffer = []
        self.last_update_time = time.time()
        self.java_process = None  # Initialize the Java process reference

        self.protocol("WM_DELETE_WINDOW", self.on_close)  # Set the close window protocol

        self.start_java_jar()
        self.check_queue()

        self.update_local_info()
        self.update_global_info()  # Initialize global info update
        self.update_info_from_file()  # Initialize info from file update

    def create_info_tab(self):
        info_tab = ttk.Frame(self.notebook)
        self.notebook.add(info_tab, text=' Info ')

        info_frame = tk.Frame(info_tab, bg='lightblue')
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.local_info = tk.Text(info_frame, height=1, width=20, bg='lightblue')
        self.local_info.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.local_info.insert(tk.END, "Local blocks")

        self.global_info = tk.Text(info_frame, height=1, width=20, bg='lightblue')
        self.global_info.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.global_info.insert(tk.END, "Global blocks")

        update_blockchain_button = tk.Button(info_frame, text="Update Blockchain", command=self.update_blockchain,
                                             bg='lightgrey')
        update_blockchain_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.combined_info = tk.Text(info_frame, height=3, width=45, bg='lightblue')
        self.combined_info.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)

        refresh_combined_button = tk.Button(info_frame, text="Refresh Balance", command=self.refresh_combined_info,
                                            bg='lightgrey')
        refresh_combined_button.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

    def update_blockchain(self):
        threading.Thread(target=self._update_blockchain).start()

    def _update_blockchain(self):
        url = "http://localhost:8082/resolving"
        response = perform_http_get(url)

    def refresh_combined_info(self):
        try:
            with open(r"C:\\resources\\server\\server.txt", "r") as server_file:
                server_ip = server_file.read().strip()

            with open(r"C:\\resources\\minerAccount\\minerAccount.txt", "r") as account_file:
                miner_account = account_file.read().strip()

            combined_url = f"{server_ip}/account?address={miner_account}"
            response = requests.get(combined_url)

            if response.status_code == 200:
                data = response.json()

                digital_dollar_balance = data.get("digitalDollarBalance", "N/A")
                digital_stock_balance = data.get("digitalStockBalance", "N/A")
                digital_staking_balance = data.get("digitalStakingBalance", "N/A")

                formatted_output = (
                    f"Digital Dollar Balance: {digital_dollar_balance}\n"
                    f"Digital Stock Balance: {digital_stock_balance}\n"
                    f"Digital Staking Balance: {digital_staking_balance}"
                )

                self.combined_info.delete(1.0, tk.END)
                self.combined_info.insert(tk.END, formatted_output)
            else:
                self.combined_info.delete(1.0, tk.END)
                self.combined_info.insert(tk.END, f"Error: Failed to fetch data. Status code: {response.status_code}")
        except Exception as e:
            self.combined_info.delete(1.0, tk.END)
            self.combined_info.insert(tk.END, f"Error reading combined info: {str(e)}")

    def update_local_info(self):
        try:
            with open(r"C:\\resources\\tempblockchain\\shortBlockchain.txt", "r") as file:
                data = json.load(file)
                size = data.get("size", "N/A")
                self.local_info.delete(1.0, tk.END)
                self.local_info.insert(tk.END, f"Local Size: {size}")
        except Exception as e:
            self.local_info.delete(1.0, tk.END)
            self.local_info.insert(tk.END, f"Error reading Local info: {str(e)}")

        self.after(10000, self.update_local_info)

    def update_global_info(self):
        try:
            with open(r"C:\\resources\\server\\server.txt", "r") as file:
                server_ip = file.read().strip()
                url = f"{server_ip}/size"
                data = perform_http_get(url)
                self.global_info.delete(1.0, tk.END)
                self.global_info.insert(tk.END, f"Global Size: {json.dumps(data, indent=2)}")
        except Exception as e:
            self.global_info.delete(1.0, tk.END)
            self.global_info.insert(tk.END, f"Error reading Global info: {str(e)}")

        self.after(10000, self.update_global_info)

    def update_info_from_file(self):
        try:
            with open(r"C:\\resources\\minerAccount\\minerAccount.txt", "r") as file:
                account_info = file.read().strip()
                if not account_info:
                    account_info = "BUDGET"
                self.miner_account_info.delete(1.0, tk.END)
                self.miner_account_info.insert(tk.END, account_info)
        except Exception as e:
            self.miner_account_info.delete(1.0, tk.END)
            self.miner_account_info.insert(tk.END, f"Error reading Miner Account info: {str(e)}")

        self.after(600000, self.update_info_from_file)

    def create_wallet_tab(self):
        wallet_tab = ttk.Frame(self.notebook)
        self.notebook.add(wallet_tab, text=' Wallet&Server ')

        wallet_frame = tk.Frame(wallet_tab, bg='lightblue')
        wallet_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        wallet_label = tk.Label(wallet_frame, text="Wallet Address", bg='lightblue')
        wallet_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.wallet_entry = ttk.Entry(wallet_frame, width=50)
        self.wallet_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        confirm_button_wallet = tk.Button(wallet_frame, text="Confirm", command=self.confirm_wallet_address,
                                          bg='lightgrey')
        confirm_button_wallet.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        self.miner_account_info = tk.Text(wallet_frame, height=1, width=45, bg='lightblue')
        self.miner_account_info.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        refresh_button = tk.Button(wallet_frame, text="Refresh", command=self.refresh_miner_account_info,
                                   bg='lightgrey')
        refresh_button.grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)

        form_label = tk.Label(wallet_frame, text="Choose Server", bg='lightblue')
        form_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)

        nodes = fetch_nodes()
        self.host_entry = ttk.Combobox(wallet_frame, values=nodes, width=50)
        self.host_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        change_server_button = tk.Button(wallet_frame, text="Change your server", command=self.change_server,
                                         bg='lightgrey')
        change_server_button.grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)

    def refresh_miner_account_info(self):
        try:
            with open(r"C:\\resources\\minerAccount\\minerAccount.txt", "r") as file:
                account_info = file.read().strip()
                if not account_info:
                    account_info = "BUDGET"
                self.miner_account_info.delete(1.0, tk.END)
                self.miner_account_info.insert(tk.END, account_info)
        except Exception as e:
            self.miner_account_info.delete(1.0, tk.END)
            self.miner_account_info.insert(tk.END, f"Error reading Miner Account info: {str(e)}")

    def confirm_wallet_address(self):
        url = "http://localhost:8082/setMinner"
        miner_address = self.wallet_entry.get()
        if not miner_address:
            self.console.insert(tk.END, "Please enter a valid wallet address.\n")
            return

        data = {"setMinner": miner_address}

        self.wallet_entry.delete(0, tk.END)
        self.console.insert(tk.END, f"Sending request to set miner address: {miner_address}\n")
        threading.Thread(target=perform_http_post_form, args=(url, data)).start()

        self.wallet_address_info.delete(1.0, tk.END)
        self.wallet_address_info.insert(tk.END, miner_address)

    def change_server(self):
        url = "http://localhost:8082/server"
        host = self.host_entry.get()
        data = {"host": host}
        response = perform_http_post_form(url, data)
        if "error" in response:
            self.console.insert(tk.END, f"Error changing server: {response['error']}\n")
        else:
            self.console.insert(tk.END, f"Server changed to: {host}\n")

    def create_mining_tab(self):
        mining_tab = ttk.Frame(self.notebook)
        self.notebook.add(mining_tab, text=' Mining ')

        mining_frame = tk.Frame(mining_tab, bg='lightblue')
        mining_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        difficulty_label = tk.Label(mining_frame, text="Difficulty", bg='lightblue')
        difficulty_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.difficulty_combobox = ttk.Combobox(mining_frame, values=[str(i) for i in range(17, 100)], width=10)
        self.difficulty_combobox.grid(row=0, column=1, padx=5, pady=5)
        self.difficulty_combobox.set("17")

        confirm_button_difficulty = tk.Button(mining_frame, text="Confirm", command=self.confirm_difficulty,
                                              bg='lightgrey')
        confirm_button_difficulty.grid(row=0, column=2, padx=5, pady=5)

        spacer = tk.Frame(mining_frame, height=30, bg='lightblue')
        spacer.grid(row=1, column=0, columnspan=3)

        start_button = tk.Button(mining_frame, text="Start Mining", command=self.start_mining, bg='lightgrey')
        start_button.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        stop_button = tk.Button(mining_frame, text="Stop Mining", command=self.stop_mining, bg='lightgrey')
        stop_button.grid(row=2, column=2, padx=5, pady=5)

    def confirm_difficulty(self):
        selected_difficulty = self.difficulty_combobox.get()
        url = "http://localhost:8082/customDiff"
        if not selected_difficulty.isdigit() or int(selected_difficulty) < 17 or int(selected_difficulty) > 99:
            self.console.insert(tk.END, "Please enter a valid difficulty between 17 and 99.\n")
            return

        data = {"customDiff": selected_difficulty}

        self.console.insert(tk.END, f"Sending request to set difficulty: {selected_difficulty}\n")
        threading.Thread(target=perform_http_post_form, args=(url, data)).start()

    def start_mining(self):
        threading.Thread(target=self._start_mining).start()

    def _start_mining(self):
        url = "http://localhost:8082/constantMining"
        perform_http_get(url)

    def stop_mining(self):
        threading.Thread(target=self._stop_mining).start()

    def _stop_mining(self):
        url = "http://localhost:8082/stopMining"
        perform_http_get(url)

    def create_staking_tab(self):
        staking_tab = ttk.Frame(self.notebook)
        self.notebook.add(staking_tab, text=' Staking&Unstaking ')

        staking_frame = tk.Frame(staking_tab, bg='lightblue')
        staking_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        staking_label = tk.Label(staking_frame, text="Address", bg='lightblue')
        staking_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        staking_label = tk.Label(staking_frame, text="Amount", bg='lightblue')
        staking_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        staking_label = tk.Label(staking_frame, text="Password", bg='lightblue')
        staking_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        staking_address_entry = tk.Entry(staking_frame, width=55)
        staking_address_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        staking_dollar_entry = tk.Entry(staking_frame, width=55)
        staking_dollar_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        staking_password_entry = tk.Entry(staking_frame, width=55)
        staking_password_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        staking_button = tk.Button(staking_frame, text="Staking",
                                   command=lambda: process_staking(staking_address_entry.get(),
                                                                   staking_dollar_entry.get(),
                                                                   staking_password_entry.get()), bg='lightgrey')
        staking_button.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        unstaking_button = tk.Button(staking_frame, text="Unstaking",
                                     command=lambda: process_unstaking(staking_address_entry.get(),
                                                                       staking_dollar_entry.get(),
                                                                       staking_password_entry.get()), bg='lightgrey')
        unstaking_button.grid(row=3, column=1, padx=5, pady=5, sticky=tk.E)

    def create_create_account_tab(self):
        create_account_tab = ttk.Frame(self.notebook)
        self.notebook.add(create_account_tab, text=' Create Account ')

        create_account_frame = tk.Frame(create_account_tab, bg='lightblue')
        create_account_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        pub_key_label = tk.Label(create_account_frame, text="Wallet", bg='lightblue')
        pub_key_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.pub_key_entry = ttk.Entry(create_account_frame, width=60)
        self.pub_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        priv_key_label = tk.Label(create_account_frame, text="Password", bg='lightblue')
        priv_key_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.priv_key_entry = ttk.Entry(create_account_frame, width=60)
        self.priv_key_entry.grid(row=1, column=1, rowspan=3, padx=5, pady=5, sticky=tk.W)

        fetch_keys_button = tk.Button(create_account_frame, text="Generate New Account", command=self.fetch_keys,
                                      bg='lightgrey')
        fetch_keys_button.grid(row=4, column=1, padx=5, pady=10, sticky=tk.W)

        backup_button = tk.Button(create_account_frame, text="Create BackUp File", command=self.create_backup_file,
                                  bg='lightgrey')
        backup_button.grid(row=4, column=1, padx=5, pady=5, sticky=tk.E)

    def fetch_keys(self):
        url = "http://localhost:8082/keys"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                keys_data = response.json()
                pub_key = keys_data.get("pubKey", "")
                priv_key = keys_data.get("privKey", "")

                self.pub_key_entry.delete(0, tk.END)
                self.pub_key_entry.insert(tk.END, pub_key)

                self.priv_key_entry.delete(0, tk.END)
                self.priv_key_entry.insert(tk.END, priv_key)
            else:
                self.console.insert(tk.END, f"Error fetching keys: Status code {response.status_code}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error fetching keys: {str(e)}\n")

    def create_backup_file(self):
        pub_key = self.pub_key_entry.get()
        priv_key = self.priv_key_entry.get()
        if not pub_key or not priv_key:
            self.console.insert(tk.END, "Both wallet and password must be provided to create a backup file.\n")
            return

        backup_filename = f"{pub_key}.txt"
        backup_filepath = os.path.join(os.getcwd(), backup_filename)

        try:
            with open(backup_filepath, 'w') as backup_file:
                backup_file.write(f"Backup for wallet: {pub_key}\n")
                backup_file.write(f"Public Key: {pub_key}\n")
                backup_file.write(f"Private Key: {priv_key}\n")
            self.console.insert(tk.END, f"Backup file created: {backup_filepath}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error creating backup file: {str(e)}\n")

    def create_send_coin_tab(self):
        send_coin_tab = ttk.Frame(self.notebook)
        self.notebook.add(send_coin_tab, text=' Sending Coins ')

        send_coin_frame = tk.Frame(send_coin_tab, bg='lightblue')
        send_coin_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        labels = ["Sender", "Recipient", "Dollar", "Stock", "Reward", "Password"]
        self.entries = {}

        for idx, label in enumerate(labels):
            tk.Label(send_coin_frame, text=label, bg='lightblue').grid(row=idx, column=0, padx=5, pady=5, sticky=tk.W)
            entry = ttk.Entry(send_coin_frame, width=55)
            entry.grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W)
            self.entries[label.lower()] = entry

        send_button = tk.Button(send_coin_frame, text="Send", command=self.send_coin, bg='lightgrey')
        send_button.grid(row=len(labels), column=1, padx=5, pady=5, sticky=tk.W)

    def send_coin(self):
        sender = self.entries['sender'].get()
        recipient = self.entries['recipient'].get()
        dollar = self.entries['dollar'].get()
        stock = self.entries['stock'].get()
        reward = self.entries['reward'].get()
        password = self.entries['password'].get()

        if not sender or not recipient or not dollar or not stock or not reward or not password:
            self.console.insert(tk.END, "All fields must be filled out.\n")
            return

        url = f"http://localhost:8082/sendCoin?sender={sender}&recipient={recipient}&dollar={dollar}&stock={stock}&reward={reward}&password={password}"
        self.console.insert(tk.END, f"Sending request: {url}\n")

        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.console.insert(tk.END, "Request successful.\n")
            else:
                self.console.insert(tk.END, f"Request failed with status code: {response.status_code}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {str(e)}\n")

    def start_java_jar(self):
        threading.Thread(target=self.run_java_jar, daemon=True).start()

    def run_java_jar(self):
        java_home = os.getenv('JAVA_HOME')
        if not java_home:
            java_home = set_java_home(self.queue)  # Předáváme správnou frontu
            if java_home:
                self.queue.put(f"JAVA_HOME set to {java_home}")
            else:
                self.queue.put("Error: Unable to find Java installation.")
                return

        java_exe = os.path.join(java_home, "bin", "java.exe")

        # Zjistí dostupné verze na GitHubu
        github_url = "https://github.com/CorporateFounder/unitedStates_final/raw/master/target/"
        try:
            response = requests.get(github_url)
            response.raise_for_status()
        except Exception as e:
            self.queue.put(f"Error accessing GitHub URL: {str(e)}")
            return

        # Extrahuje název nejnovějšího .jar souboru
        jar_pattern = re.compile(r'unitedStates-(\d+\.\d+\.\d+)-SNAPSHOT\.jar')
        match = jar_pattern.search(response.text)
        if not match:
            self.queue.put("Error: No valid .jar file found on GitHub.")
            return

        jar_version = match.group(1)
        jar_url = f"https://github.com/CorporateFounder/unitedStates_final/raw/master/target/unitedStates-{jar_version}-SNAPSHOT.jar"
        jar_path = os.path.join(f"unitedStates-{jar_version}-SNAPSHOT.jar")

        if not os.path.exists(jar_path):
            self.queue.put(f".jar file not found at {jar_path}, attempting to download...")
        try:
            jar_response = requests.get(jar_url, stream=True)
            jar_response.raise_for_status()
            with open(jar_path, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            self.queue.put(f"Error downloading .jar file: {str(e)}")
            return

        if not os.path.exists(java_exe):
            self.queue.put(f"Error: Java not found at {java_exe}")
            return

        command = [java_exe, "-jar", jar_path]

        try:
            self.java_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            for line in iter(self.java_process.stdout.readline, ''):
                with self.queue_lock:
                    self.output_buffer.append(line.strip())
                    if len(self.output_buffer) >= 10:
                        self.queue.put('\n'.join(self.output_buffer))
                        self.output_buffer.clear()

            self.java_process.wait()
            self.queue.put("Java Jar process terminated.")
        except Exception as e:
            self.queue.put(f"Error starting Java Jar: {str(e)}")

    def on_close(self):
        if self.java_process and self.java_process.poll() is None:
            self.java_process.terminate()
        self.destroy()

    def check_queue(self):
        while not self.queue.empty():
            message = self.queue.get_nowait()
            self.console.insert(tk.END, message + "\n")
            self.console.see(tk.END)
        self.after(100, self.check_queue)


if __name__ == "__main__":
    app = Application()
    app.mainloop()
