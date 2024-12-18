import json
import os
import queue
import re
import subprocess
import threading
import tkinter as tk

import customtkinter as ctk
import requests

# Inicializace stylu
ctk.set_appearance_mode("light")  # Světlý režim, možnost 'dark' pro tmavý
ctk.set_default_color_theme("blue")  # Hlavní barvy


def set_java_home(queue):
    # Kontrola, zda je JAVA_HOME již nastavena a existuje
    if 'JAVA_HOME' in os.environ and os.path.exists(os.environ['JAVA_HOME']):
        java_home = os.environ['JAVA_HOME']
        queue.put(f"JAVA_HOME is already set to: {java_home}")
        return java_home

    # Definice možných cest
    possible_paths = [
        "C:\\Program Files\\Java",
        "C:\\Program Files (x86)\\Java"
    ]

    queue.put("Searching for Java installations...")

    available_versions = []

    # Hledání JDK v možných cestách
    for path in possible_paths:
        if os.path.exists(path):
            queue.put(f"Checking path: {path}")
            java_versions = sorted(os.listdir(path), reverse=True)  # Seřadí verze sestupně
            for version in java_versions:
                full_path = os.path.join(path, version)
                if os.path.isdir(full_path):  # Ověří, že se jedná o složku
                    available_versions.append(full_path)

    # Pokud nejsou nalezeny žádné verze
    if not available_versions:
        queue.put("Error: No Java installations found.")
        return None

    # Automaticky vybere nejnovější verzi
    java_home = available_versions[0]
    queue.put(f"Detected latest JDK version: {java_home}")

    # Nastavení JAVA_HOME v aktuálním procesu
    os.environ['JAVA_HOME'] = java_home
    queue.put(f"JAVA_HOME temporarily set to: {java_home}")

    # Trvalé nastavení pomocí setx
    try:
        subprocess.run(['setx', 'JAVA_HOME', java_home], check=True)
        queue.put(f"JAVA_HOME successfully added to system environment variables: {java_home}")
    except subprocess.CalledProcessError as e:
        queue.put(f"Failed to add JAVA_HOME to system environment variables. Error: {e}")

    return java_home


def perform_http_get(url):
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def perform_http_post_form(url, data):
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


class Application(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Nastavení okna
        self.title("Welcome to the future with CITU")
        self.geometry("900x900")
        self.configure(fg_color="#B0B0B0")

        self.queue = queue.Queue()
        self.queue_lock = threading.Lock()
        self.output_buffer = []
        self.java_process = None

        # Hlavní notebook pro záložky
        self.notebook = ctk.CTkTabview(self, width=850, height=100)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        self.notebook.add("Info")
        self.notebook.add("Wallet&Server")
        self.notebook.add("Mining")
        self.notebook.add("Staking&Unstaking")
        self.notebook.add("Sending Coins")
        self.notebook.add("Create Account")

        # Přidání jednotlivých sekcí
        self.create_info_tab()
        self.create_wallet_tab()
        self.create_mining_tab()
        self.create_staking_tab()
        self.create_send_coin_tab()
        self.create_create_account_tab()

        # Konzole pro zobrazení výstupů
        self.console = ctk.CTkTextbox(self, wrap=tk.WORD, height=500, width=500, fg_color="black", text_color="white")
        self.console.pack(fill="both", expand=True, padx=10, pady=10)

        # Automatické procesy
        self.start_java_jar()
        self.check_queue()

        # Zajistí správné zavření aplikace
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_info_tab(self):
        # Vytvoření záložky
        info_tab = self.notebook.tab("Info")

        # Hlavní rám pro záložku
        info_frame = ctk.CTkFrame(info_tab, fg_color="#B0B0B0")
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Textové pole pro lokální bloky
        local_info_label = ctk.CTkLabel(info_frame, text="Blockchain Info:", text_color="#1A1A1A")
        local_info_label.grid(row=0, column=1, padx=5, pady=5, sticky="")

        self.local_info = ctk.CTkTextbox(info_frame, height=1, width=200, fg_color="white", text_color="black")
        self.local_info.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.local_info.insert("1.0", "Local blocks: N/A")
        self.local_info.configure(state="disabled")  # Zamezení editace

        # Textové pole pro globální bloky
        self.global_info = ctk.CTkTextbox(info_frame, height=1, width=200, fg_color="white", text_color="black")
        self.global_info.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.global_info.insert("1.0", "Global blocks: N/A")
        self.global_info.configure(state="disabled")  # Zamezení editace

        # Tlačítko pro aktualizaci blockchainu
        update_blockchain_button = ctk.CTkButton(
            info_frame, text="Update Blockchain", command=self.update_blockchain, fg_color="#1E1E1E", text_color="white"
        )
        update_blockchain_button.grid(row=3, column=1, padx=10, pady=5, sticky="")

        # Spuštění aktualizací
        self.update_local_info()
        self.update_global_info()

        # Prázdná mezera mezi sloupci
        spacer = ctk.CTkLabel(info_frame, text="", width=200)  # Prázdný widget jako mezera
        spacer.grid(row=0, column=2, rowspan=4)  # Zabereme prostor mezi column=1 a column=3

        # Dollar Balance Label
        dollar_balance_label = ctk.CTkLabel(
            info_frame, text="Dollar Balance:", text_color="#1A1A1A"
        )
        dollar_balance_label.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        # Dollar Balance Textbox
        self.dollar_balance_info = ctk.CTkTextbox(
            info_frame, height=30, width=400, fg_color="white", text_color="black"
        )
        self.dollar_balance_info.grid(row=0, column=3, padx=10, pady=5, sticky="e")
        self.dollar_balance_info.insert("1.0", "Dollar Balance: N/A")
        self.dollar_balance_info.configure(state="disabled")  # Zamezení editace

        # Stock Balance Label
        stock_balance_label = ctk.CTkLabel(
            info_frame, text="Stock Balance:", text_color="#1A1A1A"
        )
        stock_balance_label.grid(row=1, column=2, padx=10, pady=5, sticky="e")

        # Stock Balance Textbox
        self.stock_balance_info = ctk.CTkTextbox(
            info_frame, height=30, width=400, fg_color="white", text_color="black"
        )
        self.stock_balance_info.grid(row=1, column=3, padx=10, pady=5, sticky="e")
        self.stock_balance_info.insert("1.0", "Stock Balance: N/A")
        self.stock_balance_info.configure(state="disabled")  # Zamezení editace

        # Staking Balance Label
        staking_balance_label = ctk.CTkLabel(
            info_frame, text="Staking Balance:", text_color="#1A1A1A"
        )
        staking_balance_label.grid(row=2, column=2, padx=10, pady=5, sticky="e")

        # Staking Balance Textbox
        self.staking_balance_info = ctk.CTkTextbox(
            info_frame, height=30, width=400, fg_color="white", text_color="black"
        )
        self.staking_balance_info.grid(row=2, column=3, padx=10, pady=5, sticky="e")
        self.staking_balance_info.insert("1.0", "Staking Balance: N/A")
        self.staking_balance_info.configure(state="disabled")  # Zamezení editace

        # Refresh Button
        refresh_combined_button = ctk.CTkButton(
            info_frame, text="Refresh Balance", command=self.refresh_combined_info, fg_color="#1E1E1E",
            text_color="white"
        )
        refresh_combined_button.grid(row=3, column=3, padx=10, pady=5, sticky="")

    def create_wallet_tab(self):
        # Vytvoření záložky Wallet&Server
        frame = ctk.CTkFrame(self.notebook.tab("Wallet&Server"), fg_color="#B0B0B0")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Wallet Address Label
        wallet_label = ctk.CTkLabel(frame, text="Add/Change Wallet Address:", text_color="#1A1A1A")
        wallet_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Wallet Address Entry
        self.wallet_entry = ctk.CTkEntry(frame, width=350)
        self.wallet_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Confirm Button
        confirm_button = ctk.CTkButton(
            frame, text="Confirm", command=self.confirm_wallet_address, fg_color="#1E1E1E", text_color="white"
        )
        confirm_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Miner Account Info Text
        miner_account_label = ctk.CTkLabel(frame, text="Chosen wallet Info:", text_color="#1A1A1A")
        miner_account_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.miner_account_info = ctk.CTkTextbox(frame, height=30, width=350, fg_color="white", text_color="black")
        self.miner_account_info.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.miner_account_info.insert("0.0", "Miner account info will be displayed here.")
        self.miner_account_info.configure(state="disabled")  # Zamezení editace

        # Refresh Button
        refresh_button = ctk.CTkButton(
            frame, text="Refresh", command=self.refresh_miner_account_info, fg_color="#1E1E1E", text_color="white"
        )
        refresh_button.grid(row=2, column=2, padx=5, pady=5, sticky="w")

        # Choose Server Label
        server_label = ctk.CTkLabel(frame, text="Choose Server:", text_color="#1A1A1A")
        server_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")

        # Server Combobox
        nodes = self.fetch_nodes()  # Získání seznamu serverů
        self.host_entry = ctk.CTkComboBox(frame, values=nodes, width=350)
        self.host_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # Change Server Button
        change_server_button = ctk.CTkButton(
            frame, text="Change your server", command=self.change_server, fg_color="#1E1E1E", text_color="white"
        )
        change_server_button.grid(row=4, column=2, padx=5, pady=5, sticky="w")

    def create_mining_tab(self):
        # Vytvoření záložky Mining
        frame = ctk.CTkFrame(self.notebook.tab("Mining"), fg_color="#B0B0B0")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Štítek pro nastavení obtížnosti
        difficulty_label = ctk.CTkLabel(frame, text="Mining Difficulty:", text_color="#1A1A1A")
        difficulty_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Rozevírací menu s možností rolování
        self.difficulty_option_menu = ctk.CTkOptionMenu(
            frame,
            values=[str(i) for i in range(17, 100)],  # Hodnoty pro výběr
            width=50,
            fg_color="white",
            text_color="black"
        )
        self.difficulty_option_menu.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.difficulty_option_menu.set("17")  # Výchozí hodnota

        # Tlačítko pro potvrzení obtížnosti
        confirm_button_difficulty = ctk.CTkButton(
            frame, text="Confirm", command=self.confirm_difficulty, fg_color="#1E1E1E", text_color="white"
        )
        confirm_button_difficulty.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Spacer pro oddělení widgetů
        spacer = ctk.CTkLabel(frame, text="", width=1, height=30)  # Prázdný widget jako mezera
        spacer.grid(row=1, column=0, columnspan=3)

        # Tlačítko pro spuštění těžby
        start_button = ctk.CTkButton(
            frame, text="Start Mining", command=self.start_mining, fg_color="#1E1E1E", text_color="white"
        )
        start_button.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # Tlačítko pro zastavení těžby
        stop_button = ctk.CTkButton(
            frame, text="Stop Mining", command=self.stop_mining, fg_color="#1E1E1E", text_color="white"
        )
        stop_button.grid(row=2, column=2, padx=5, pady=5, sticky="e")

    def create_staking_tab(self):
        # Vytvoření záložky Staking&Unstaking
        frame = ctk.CTkFrame(self.notebook.tab("Staking&Unstaking"), fg_color="#B0B0B0")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Štítky pro zadání údajů
        staking_address_label = ctk.CTkLabel(frame, text="Address:", text_color="#1A1A1A")
        staking_address_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        staking_amount_label = ctk.CTkLabel(frame, text="Dollar:", text_color="#1A1A1A")
        staking_amount_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        staking_password_label = ctk.CTkLabel(frame, text="Password:", text_color="#1A1A1A")
        staking_password_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # Vstupní pole pro zadání adresy
        self.staking_address_entry = ctk.CTkEntry(frame, width=350, fg_color="white", text_color="black")
        self.staking_address_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Registrace validace
        validate_command = self.register(self.validate_decimal)

        # Vstupní pole pro zadání částky
        self.staking_amount_entry = ctk.CTkEntry(
            frame,
            width=350,
            fg_color="white",
            text_color="black",
            validate="key",
            validatecommand=(validate_command, "%P")  # Volání validace
        )
        self.staking_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Vstupní pole pro heslo (skryté znaky)
        self.staking_password_entry = ctk.CTkEntry(frame, width=350, fg_color="white", text_color="black", show="*")
        self.staking_password_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Přidání tlačítka Show pro zobrazení hesla
        show_password_button = ctk.CTkButton(
            frame,
            text="Show",
            command=lambda: self.toggle_password(self.staking_password_entry),  # Předání konkrétního pole
            fg_color="#1E1E1E",
            text_color="white",
            width=70
        )
        show_password_button.grid(row=2, column=2, padx=5, pady=5, sticky="w")

        # Tlačítko pro staking
        staking_button = ctk.CTkButton(
            frame, text="Stake", command=self.staking_action, fg_color="#1E1E1E", text_color="white"
        )
        staking_button.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Tlačítko pro unstaking
        unstaking_button = ctk.CTkButton(
            frame, text="Unstake", command=self.unstaking_action, fg_color="#1E1E1E", text_color="white"
        )
        unstaking_button.grid(row=3, column=1, padx=5, pady=5, sticky="e")

    def create_send_coin_tab(self):
        # Vytvoření záložky Sending Coins
        frame = ctk.CTkFrame(self.notebook.tab("Sending Coins"), fg_color="#B0B0B0")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Seznam popisků polí
        labels = ["Sender", "Recipient", "Dollar", "Stock", "Reward", "Password"]
        self.entries = {}

        # Registrace validace pro použití s Entry widgetem
        validate_command = self.register(self.validate_decimal)

        # Vytvoření polí a tlačítek
        for idx, label in enumerate(labels):
            # Štítky
            ctk.CTkLabel(frame, text=label, text_color="#1A1A1A").grid(row=idx, column=0, padx=5, pady=5, sticky="w")

            # Vstupní pole
            entry = ctk.CTkEntry(frame, width=350, fg_color="white", text_color="black")

            # Validace pro pole Dollar, Stock a Reward
            if label in ["Dollar", "Stock", "Reward"]:
                entry.insert(0, "0.0")
                entry.configure(validate="key", validatecommand=(validate_command, "%P"))

            # Nastavení pole pro heslo
            if label == "Password":
                entry.configure(show="*")

            entry.grid(row=idx, column=1, padx=5, pady=5, sticky="w")
            self.entries[label.lower()] = entry

            # Tlačítko pro zobrazení hesla
            if label == "Password":
                show_password_button = ctk.CTkButton(
                    frame,
                    text="Show",
                    command=lambda e=entry: self.toggle_password(e),  # Předání konkrétního widgetu
                    fg_color="#1E1E1E",
                    text_color="white",
                    width=70
                )
                show_password_button.grid(row=idx, column=2, padx=5, pady=5, sticky="w")

        # Tlačítko pro odeslání transakce
        send_button = ctk.CTkButton(
            frame, text="Send Coins", command=self.send_coin, fg_color="#1E1E1E", text_color="white"
        )
        send_button.grid(row=len(labels), column=1, padx=5, pady=5, sticky="w")

    def create_create_account_tab(self):
        # Vytvoření záložky Create Account
        frame = ctk.CTkFrame(self.notebook.tab("Create Account"), fg_color="#B0B0B0")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Štítek a vstupní pole pro Wallet
        wallet_label = ctk.CTkLabel(frame, text="Wallet:", text_color="#1A1A1A")
        wallet_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.pub_key_entry = ctk.CTkEntry(frame, width=350, fg_color="white", text_color="black")
        self.pub_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Štítek a vstupní pole pro Password
        password_label = ctk.CTkLabel(frame, text="Password:", text_color="#1A1A1A")
        password_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Víceřádkové pole pro zadání hesla (skryté výchozí nastavení)
        self.priv_key_entry = ctk.CTkTextbox(
            frame, height=100, width=350, fg_color="white", text_color="black", wrap="word"
        )
        self.priv_key_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.priv_key_entry.insert("1.0", "*" * 20)  # Výchozí zobrazení jako hvězdičky
        self.priv_key_entry.configure(state="disabled")  # Zamezení editace pole

        # Výchozí stav - heslo je skryté
        self.is_password_hidden = True
        self.original_password = ""  # Uchovává skutečné heslo

        # Tlačítko Show pro zobrazení/skrývání hesla
        toggle_password_button = ctk.CTkButton(
            frame,
            text="Show",
            command=lambda: self.toggle_password_textbox(toggle_password_button),
            fg_color="#1E1E1E",
            text_color="white",
            width=70
        )
        toggle_password_button.grid(row=1, column=2, padx=5, pady=5, sticky="w")

        # Tlačítko pro generování nového účtu
        fetch_keys_button = ctk.CTkButton(
            frame, text="Generate New Account", command=self.fetch_keys, fg_color="#1E1E1E", text_color="white"
        )
        fetch_keys_button.grid(row=4, column=1, padx=5, pady=10, sticky="w")

        # Tlačítko pro vytvoření záložního souboru
        backup_button = ctk.CTkButton(
            frame, text="Create BackUp File", command=self.create_backup_file, fg_color="#1E1E1E", text_color="white"
        )
        backup_button.grid(row=4, column=1, padx=5, pady=5, sticky="e")

    # Metoda pro přepínání stavu zobrazení hesla
    def toggle_password_textbox(self, button):
        """Přepne mezi zobrazením a skrytím hesla."""
        if self.is_password_hidden:
            # Přepnout na zobrazení hesla
            self.priv_key_entry.configure(state="normal")  # Povolit editaci
            self.priv_key_entry.delete("1.0", "end")
            self.priv_key_entry.insert("1.0", self.original_password)
            self.priv_key_entry.configure(state="disabled")  # Zamezit editaci
            button.configure(text="Hide")
        else:
            # Přepnout na skrytí hesla
            self.original_password = self.priv_key_entry.get("1.0", "end").strip()  # Uložit skutečné heslo
            self.priv_key_entry.configure(state="normal")  # Povolit editaci
            self.priv_key_entry.delete("1.0", "end")
            self.priv_key_entry.insert("1.0", "*" * len(self.original_password))
            self.priv_key_entry.configure(state="disabled")  # Zamezit editaci
            button.configure(text="Show")
        self.is_password_hidden = not self.is_password_hidden

    def validate_decimal(self, new_value):
        """
        Validates that the input is a valid decimal number with up to two decimal places.
        Only allows a dot (.) as the decimal separator.
        """
        if new_value == "" or re.match(r'^\d*\.?\d{0,2}$', new_value):
            return True
        return False

    def fetch_nodes(self):
        url = "http://194.87.236.238:82/getNodes"
        try:
            response = requests.get(url)
            nodes = response.json()
            return nodes
        except Exception as e:
            return {"error": str(e)}

    def update_blockchain(self):
        # Spustí aktualizaci v jiném vlákně
        threading.Thread(target=self._update_blockchain, daemon=True).start()

    def _update_blockchain(self):
        url = "http://localhost:8082/resolving"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                message = "Blockchain updated successfully.\n"
            else:
                message = f"Failed to update blockchain. Status code: {response.status_code}\n"
        except Exception as e:
            message = f"Error updating blockchain: {str(e)}\n"

        # Výsledek vloží do fronty, aby ho GUI zpracovalo
        self.queue.put(message)

    def update_local_info(self):
        try:
            with open(r"C:\\resources\\tempblockchain\\shortBlockchain.txt", "r") as file:
                data = json.load(file)
                size = data.get("size", "N/A")
                self.local_info.configure(state="normal")
                self.local_info.delete("1.0", tk.END)
                self.local_info.insert("1.0", f"Local Size: {size}")
                self.local_info.configure(state="disabled")
        except Exception as e:
            self.local_info.configure(state="normal")
            self.local_info.delete("1.0", tk.END)
            self.local_info.insert("1.0", f"Error: {e}")
            self.local_info.configure(state="disabled")

        # Automatická aktualizace každých 10 sekund
        self.after(10000, self.update_local_info)

    def update_global_info(self):
        try:
            with open(r"C:\\resources\\server\\server.txt", "r") as file:
                server_ip = file.read().strip()
                url = f"{server_ip}/size"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.global_info.configure(state="normal")
                    self.global_info.delete("1.0", tk.END)
                    self.global_info.insert("1.0", f"Global Size: {data}")
                    self.global_info.configure(state="disabled")
                else:
                    raise Exception(f"HTTP Error: {response.status_code}")
        except Exception as e:
            self.global_info.configure(state="normal")
            self.global_info.delete("1.0", tk.END)
            self.global_info.insert("1.0", f"Error: {e}")
            self.global_info.configure(state="disabled")

        # Automatická aktualizace každých 10 sekund
        self.after(10000, self.update_global_info)

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

                self.dollar_balance_info.configure(state="normal")
                self.dollar_balance_info.delete("1.0", tk.END)
                self.dollar_balance_info.insert("1.0", f"{digital_dollar_balance}")
                self.dollar_balance_info.configure(state="disabled")

                self.stock_balance_info.configure(state="normal")
                self.stock_balance_info.delete("1.0", tk.END)
                self.stock_balance_info.insert("1.0", f"{digital_stock_balance}")
                self.stock_balance_info.configure(state="disabled")

                self.staking_balance_info.configure(state="normal")
                self.staking_balance_info.delete("1.0", tk.END)
                self.staking_balance_info.insert("1.0", f"{digital_staking_balance}")
                self.staking_balance_info.configure(state="disabled")

            else:
                self.console.insert(tk.END, f"Failed to refresh balance: {response.status_code}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error refreshing balance: {str(e)}\n")

    def update_info_from_file(self):
        try:
            with open(r"C:\\resources\\minerAccount\\minerAccount.txt", "r") as file:
                account_info = file.read().strip()
                self.console.insert(tk.END, f"Account info updated: {account_info}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error reading account info: {e}\n")

        self.after(600000, self.update_info_from_file)

    def refresh_miner_account_info(self):
        try:
            # Otevření souboru a načtení obsahu
            with open(r"C:\\resources\\minerAccount\\minerAccount.txt", "r") as file:
                account_info = file.read().strip()
                # Pokud je soubor prázdný, zobrazíme výchozí text
                if not account_info:
                    account_info = "BUDGET"
                # Přepnutí pole do režimu "normal" pro úpravu
                self.miner_account_info.configure(state="normal")
                self.miner_account_info.delete("1.0", tk.END)
                self.miner_account_info.insert("1.0", account_info)
                # Nastavení pole zpět na "disabled"
                self.miner_account_info.configure(state="disabled")
        except Exception as e:
            # Zpracování chyb při načítání souboru
            self.miner_account_info.configure(state="normal")
            self.miner_account_info.delete("1.0", tk.END)
            self.miner_account_info.insert("1.0", f"Error: {e}")
            self.miner_account_info.configure(state="disabled")

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
        host = self.host_entry.get()
        if not host:
            self.console.insert(tk.END, "Please select a valid server.\n")
            return

        url = "http://localhost:8082/server"
        data = {"host": host}
        try:
            # Odeslání POST požadavku
            response = perform_http_post_form(url, data)
            if "error" in response:
                self.console.insert(tk.END, f"Error changing server: {response['error']}\n")
            else:
                self.console.insert(tk.END, f"Server changed to: {host}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {e}\n")

    def confirm_difficulty(self):
        selected_difficulty = self.difficulty_option_menu.get()
        url = "http://localhost:8082/customDiff"
        try:
            # Validace hodnoty obtížnosti
            if not selected_difficulty.isdigit() or int(selected_difficulty) < 17 or int(selected_difficulty) > 99:
                self.console.insert(tk.END, "Please enter a valid difficulty between 17 and 99.\n")
                return

            data = {"customDiff": selected_difficulty}

            # Odeslání POST požadavku
            response = perform_http_post_form(url, data)
            if "error" in response:
                self.console.insert(tk.END, f"Error setting difficulty: {response['error']}\n")
            else:
                self.console.insert(tk.END, f"Difficulty set to: {selected_difficulty}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {e}\n")

    def start_mining(self):
        # Spustíme těžbu ve vlákně
        threading.Thread(target=self._start_mining, daemon=True).start()

    def _start_mining(self):
        url = "http://localhost:8082/constantMining"
        try:
            # Volání GET požadavku
            response = perform_http_get(url)
            if "error" in response:
                self.console.insert(tk.END, f"Error starting mining: {response['error']}\n")
            else:
                self.console.insert(tk.END, "Mining started successfully.\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {e}\n")

    def stop_mining(self):
        # Zastavíme těžbu ve vlákně
        threading.Thread(target=self._stop_mining, daemon=True).start()

    def _stop_mining(self):
        url = "http://localhost:8082/stopMining"
        try:
            # Volání GET požadavku
            response = perform_http_get(url)
            if "error" in response:
                self.console.insert(tk.END, f"Error stopping mining: {response['error']}\n")
            else:
                self.console.insert(tk.END, "Mining stopped successfully.\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {e}\n")

    def staking_action(self):
        """
        Perform staking action by sending POST request to the server.
        """
        miner = self.staking_address_entry.get()
        dollar = self.staking_amount_entry.get()
        password = self.staking_password_entry.get()

        if not miner or not dollar or not password:
            self.show_error("All fields must be filled out.")
            return

        try:
            dollar = float(dollar)
            if dollar <= 0:
                self.show_error("Amount must be greater than 0.")
                return
        except ValueError:
            self.show_error("Amount must be a valid number.")
            return

        # Připrava dat jako formulářových parametrů
        data = {
            "miner": miner,
            "dollar": str(dollar),  # Server očekává číslo jako string
            "password": password
        }
        url = "http://localhost:8082/staking"
        threading.Thread(target=self.perform_post_request, args=(url, data)).start()

    def unstaking_action(self):
        """
        Perform unstaking action by sending POST request to the server.
        """
        miner = self.staking_address_entry.get()
        dollar = self.staking_amount_entry.get()
        password = self.staking_password_entry.get()

        if not miner or not dollar or not password:
            self.show_error("All fields must be filled out.")
            return

        try:
            dollar = float(dollar)
            if dollar <= 0:
                self.show_error("Amount must be greater than 0.")
                return
        except ValueError:
            self.show_error("Amount must be a valid number.")
            return

        # Připrava dat jako formulářových parametrů
        data = {
            "miner": miner,
            "dollar": str(dollar),
            "password": password
        }
        url = "http://localhost:8082/unstaking"
        threading.Thread(target=self.perform_post_request, args=(url, data)).start()

    def show_message(self, message):
        print(f"INFO: {message}")

    def show_error(self, error):
        print(f"ERROR: {error}")

    def fetch_keys(self):
        """Metoda pro generování nového účtu."""
        url = "http://localhost:8082/keys"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                keys_data = response.json()
                pub_key = keys_data.get("pubKey", "")
                priv_key = keys_data.get("privKey", "")

                # Aktualizace hodnot v GUI
                self.pub_key_entry.delete(0, "end")  # Vymaže obsah pole Wallet
                self.pub_key_entry.insert(0, pub_key)  # Vloží novou hodnotu do Wallet

                # Uložení a zobrazení hesla
                self.original_password = priv_key
                self.priv_key_entry.configure(state="normal")  # Povolit změnu
                self.priv_key_entry.delete("1.0", "end")  # Vymazání pole
                self.priv_key_entry.insert("1.0", "*" * len(priv_key))  # Zobrazení hesla jako hvězdičky
                self.priv_key_entry.configure(state="disabled")  # Zamezení editace
                self.is_password_hidden = True  # Heslo je skryté
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

    def validate_decimal(self, new_value):
        """
        Validates that the input is a valid decimal number with up to two decimal places.
        """
        # Povolí prázdný vstup (pro mazání) nebo čísla s tečkou jako desetinným oddělovačem
        if new_value == "" or re.match(r'^\d*\.?\d{0,2}$', new_value):
            return True
        return False

    def toggle_password(self, entry):
        """
        Toggles the visibility of the password field.
        """
        if entry.cget('show') == "*":
            entry.configure(show="")  # Zobrazení textu
        else:
            entry.configure(show="*")  # Skrytí textu

    def send_coin(self):
        sender = self.entries['sender'].get()
        recipient = self.entries['recipient'].get()
        dollar = self.entries['dollar'].get()
        stock = self.entries['stock'].get()
        reward = self.entries['reward'].get()
        password = self.entries['password'].get()

        # Ověření vstupů
        if not sender or not recipient or not dollar or not stock or not reward or not password:
            self.console.insert(tk.END, "All fields must be filled out.\n")
            return

        try:
            # Kontrola číselných hodnot
            dollar = float(dollar)
            stock = float(stock)
            reward = float(reward)

            if dollar <= 0 or stock < 0 or reward < 0:
                self.console.insert(tk.END, "Dollar must be greater than 0, and stock/reward must be non-negative.\n")
                return
        except ValueError:
            self.console.insert(tk.END, "Dollar, stock, and reward must be numeric values.\n")
            return

        # Konstruování URL s parametry
        url = (
            f"http://localhost:8082/sendCoin?sender={sender}&recipient={recipient}&dollar={dollar}&stock={stock}&reward={reward}&password={password}"
        )

        # Výpis odesílaného požadavku
        self.console.insert(tk.END, f"Sending request: {url}\n")

        # Odeslání GET požadavku ve vlákně
        threading.Thread(target=self.perform_get_request, args=(url,)).start()

    def perform_post_request(self, url, data):
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                self.console.insert(tk.END, "Request successful.\n")
            else:
                self.console.insert(tk.END, f"Request failed with status code: {response.status_code}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {str(e)}\n")

    def perform_get_request(self, url):
        """
        Odesílá GET požadavek na server a zpracovává odpověď.
        """
        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.console.insert(tk.END, "Request successful.\n")
                self.console.insert(tk.END, f"Response: {response.json()}\n")
            else:
                self.console.insert(tk.END, f"Request failed with status code: {response.status_code}\n")
                self.console.insert(tk.END, f"Response: {response.text}\n")
        except Exception as e:
            self.console.insert(tk.END, f"Error: {str(e)}\n")

    def start_java_jar(self):
        threading.Thread(target=self.run_java_jar, daemon=True).start()

    def run_java_jar(self):
        java_home = os.getenv('JAVA_HOME')
        if not java_home:
            java_home = set_java_home(self.queue)  # Předáváme správnou frontu
            if java_home:
                self.queue.put(
                    f"****************************************************************************************")
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
                    if len(self.output_buffer) >= 1:
                        self.queue.put('\n'.join(self.output_buffer))
                        self.output_buffer.clear()

            self.java_process.wait()
            self.queue.put("Java Jar process terminated.")
        except Exception as e:
            self.queue.put(f"Error starting Java Jar: {str(e)}")

    def on_close(self):
        """
        Ukončí proces Java a GUI aplikaci při zavření hlavního okna.
        """
        if self.java_process and self.java_process.poll() is None:
            self.java_process.terminate()  # Požádá proces o ukončení
            try:
                self.java_process.wait(timeout=5)  # Počká až 5 sekund na ukončení
            except subprocess.TimeoutExpired:
                self.java_process.kill()  # Pokud proces neodpovídá, násilně ho ukončí
        self.destroy()  # Zavře GUI aplikaci

    def update_console(self, message):
        """Bezpečná aktualizace konzole, zarovnání zpráv pod sebou."""
        if not message.endswith("\n"):
            message += "\n"  # Přidá nový řádek, pokud chybí
        self.console.insert(tk.END, message)  # Vloží text na konec
        self.console.see(tk.END)  # Posune konzoli na konec

    def check_queue(self):
        """Pravidelně kontroluje frontu a zajišťuje zobrazení zpráv pod sebou."""
        while not self.queue.empty():
            try:
                message = self.queue.get_nowait()
                self.after(0, self.update_console, message)  # Bezpečné volání do hlavního vlákna
            except queue.Empty:
                pass
        self.after(10, self.check_queue)  # Pravidelná kontrola fronty


if __name__ == "__main__":
    app = Application()
    app.mainloop()
