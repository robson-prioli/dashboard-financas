import tkinter as tk
from tkinter import Toplevel, messagebox, Listbox, MULTIPLE
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import mplcursors
import json
import os
import csv
import threading

# Configurações iniciais
stock_data = {}
update_interval = 15  # Intervalo de atualização em segundos (5 minutos)
next_update_time = None
threads = []

def get_stock_price(stock_symbol):
    # Configurar o WebDriver do Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Executar em modo headless, sem abrir a janela do navegador
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(f"https://www.google.com/search?q={stock_symbol}+stock")
        time.sleep(2)  # Aguardar a página carregar
        
        price_element = driver.find_element(By.CSS_SELECTOR, "span[jsname='vWLAgc']")
        price_text = price_element.text
        # Substituir vírgula por ponto
        if ',' in price_text:
            price_text = price_text.replace(',', '.')
        price = float(price_text)
        return price
    
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None
    
    finally:
        driver.quit()

def save_stock_data(stock_symbol, timestamp, price):
    filename = f"{stock_symbol}.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["timestamp", "price"])  # Cabeçalho
        writer.writerow([timestamp, price])

def load_stock_data(stock_symbol):
    filename = f"{stock_symbol}.csv"
    data = []
    
    if os.path.isfile(filename):
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Pular cabeçalho
            for row in reader:
                timestamp = datetime.fromisoformat(row[0])
                price = float(row[1])
                data.append((timestamp, price))
    
    return data

def fetch_stock_data(stock_symbol):
    price = get_stock_price(stock_symbol)
    if price is not None:
        now = datetime.now()
        if stock_symbol not in stock_data:
            stock_data[stock_symbol] = load_stock_data(stock_symbol)
        stock_data[stock_symbol].append((now, price))
        save_stock_data(stock_symbol, now.isoformat(), price)
    
    if all(not thread.is_alive() for thread in threads):
        update_plot()
        display_gains_losses()

def update_plot():
    ax.clear()
    for stock_symbol, data in stock_data.items():
        ax.plot([d[0] for d in data], [d[1] for d in data], marker='o', label=stock_symbol.upper())
    
    ax.set_title('Intraday Stock Prices')
    ax.set_xlabel('Time')
    ax.set_ylabel('Price')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), ncol=1, borderaxespad=0, frameon=False)
    fig.autofmt_xdate()
    canvas.draw()

    # Adiciona interatividade
    cursor = mplcursors.cursor(ax, hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text(f'Time: {sel.target[0]}\nPrice: {sel.target[1]}'))

def update_data():
    global next_update_time, threads
    threads = []
    for stock_symbol in [stock["symbol"] for stock in stocks_to_monitor]:
        thread = threading.Thread(target=fetch_stock_data, args=(stock_symbol,))
        thread.start()
        threads.append(thread)
    
    check_threads()
    next_update_time = datetime.now() + timedelta(seconds=update_interval)
    update_timer()

def check_threads():
    if all(not thread.is_alive() for thread in threads):
        update_plot()
        display_gains_losses()
    else:
        root.after(100, check_threads)

def update_timer():
    if next_update_time:
        remaining_time = next_update_time - datetime.now()
        minutes, seconds = divmod(remaining_time.seconds, 60)
        timer_label.config(text=f"Next update in: {minutes:02d}:{seconds:02d}")
        if remaining_time > timedelta(0):
            root.after(1000, update_timer)
        else:
            update_data()

def open_new_window():
    new_window = Toplevel(root)
    new_window.title("Enter Stock Symbol")

    tk.Label(new_window, text="Stock Symbol:").pack(pady=5)
    stock_entry = tk.Entry(new_window, width=20)
    stock_entry.pack(pady=5)
    
    tk.Button(new_window, text="Add", command=lambda: add_stock_symbol(stock_entry.get()), bg='white').pack(pady=5)

def add_stock_symbol(stock_symbol):
    stock_symbol = stock_symbol.upper()
    if stock_symbol and stock_symbol not in [stock["symbol"] for stock in stocks_to_monitor]:
        stocks_to_monitor.append({"symbol": stock_symbol})
        stock_listbox.insert(tk.END, stock_symbol)
        save_config({"stocks": stocks_to_monitor})
    
    update_data()

def display_gains_losses():
    results = []
    for stock in stocks_to_monitor:
        symbol = stock["symbol"]
        if symbol in stock_data and stock_data[symbol]:
            latest_price = stock_data[symbol][-1][1]
            results.append(f"{symbol}: Latest Price ${latest_price:.2f}")
        else:
            results.append(f"{symbol}: No data available")
    
    gains_losses_label.config(text="\n".join(results))
    func()

def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as file:
            return json.load(file)
    return {"stocks": []}

def save_config(data):
    with open('config.json', 'w') as file:
        json.dump(data, file, indent=4)

def func():
    for stock in stocks_to_monitor:
        symbol = stock["symbol"]
        print(f'stock: {list(stock)}')
        print(f'stock_data: {list(stock_data)}')
        #if symbol in stock_data and stock_data[symbol]:    
        #latest_price = stock_data[symbol][-1][1]

config_data = load_config()
stocks_to_monitor = config_data["stocks"]

# Configuração da interface gráfica
root = tk.Tk()
root.title("Stock Price Tracker")

# Frame para a lista de ações e o timer
left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

tk.Button(left_frame, text="Enter Stock Symbol", command=open_new_window).pack(pady=5)
stock_listbox = Listbox(left_frame, selectmode=MULTIPLE)
stock_listbox.pack(pady=5, fill=tk.BOTH, expand=False)

timer_label = tk.Label(left_frame, text="Next update in: --:--")
timer_label.pack(pady=5)

tk.Button(left_frame, text="Show Prices", command=display_gains_losses).pack(pady=5)
tk.Button(left_frame, text="Start Tracking", command=update_data).pack(pady=5)

gains_losses_label = tk.Label(left_frame, text="")
gains_losses_label.pack(pady=5)


# Frame para o gráfico
frame = tk.Frame(root, bd=2, relief='sunken')
frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

fig, ax = plt.subplots(figsize=(8, 4))
canvas = FigureCanvasTkAgg(fig, master=frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


# Frame para o gráfico do total
#frameTotal = tk.Frame(root)
#frameTotal.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)

#figTotal, axTotal = plt.subplots(figsize=(8, 4))
#canvas = FigureCanvasTkAgg(figTotal, master=frameTotal)
#canvas.get_tk_widget().pack(fill=tk.BOTH, expand=False)


#frame2 = tk.Frame(root)
#frame2.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

#timer_label3 = tk.Label(frame2, text="3333")
#timer_label3.pack(pady=5)

# Carregar dados históricos ao iniciar o programa
for stock in stocks_to_monitor:
    symbol = stock["symbol"]
    stock_data[symbol] = load_stock_data(symbol)

root.mainloop()
