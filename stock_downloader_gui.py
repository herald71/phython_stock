# ============================================================
# Program Name : stock_downloader_gui_pro_v3.py
# Created Date : 2026-03-01
# Version      : 3.0 (Auto CPU + Retry + Log Excel)
# Description  : Professional Stock Downloader GUI
# ============================================================

import os
import pandas as pd
import FinanceDataReader as fdr
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


excel_path = None


# -----------------------------
# Select Excel File
# -----------------------------
def select_file():
    global excel_path
    excel_path = filedialog.askopenfilename(
        title="Select Ticker Excel File",
        filetypes=[("Excel Files", "*.xlsx")]
    )
    if excel_path:
        log_text.insert(tk.END, f"Selected File: {excel_path}\n")


# -----------------------------
# Calculate Start Date
# -----------------------------
def calculate_start_date():
    today = datetime.today()
    option = period_var.get()

    if option == "1 Year":
        return today - timedelta(days=365)
    elif option == "3 Years":
        return today - timedelta(days=365*3)
    elif option == "10 Years":
        return today - timedelta(days=365*10)
    elif option == "Custom":
        try:
            return datetime.strptime(custom_entry.get(), "%Y-%m-%d")
        except:
            messagebox.showerror("Error", "Custom date format must be YYYY-MM-DD")
            return None


# -----------------------------
# Download with Retry
# -----------------------------
def download_with_retry(row, start_str, today_str, folder_name):
    ticker = str(row["티커"]).strip()
    ticker_name = str(row["티커명"]).strip()

    for attempt in range(2):  # 1회 재시도
        try:
            df = fdr.DataReader(ticker, start=start_str)

            file_name = f"{ticker_name}_{start_str}_{today_str}.xlsx"
            file_path = os.path.join(folder_name, file_name)
            # 시트명을 "티커명_티커" 형식으로 설정 (최대 31자 제한 고려)
            sheet_name = f"{ticker_name}_{ticker}"[:31]
            df.to_excel(file_path, sheet_name=sheet_name)

            return {"Ticker": ticker,
                    "Name": ticker_name,
                    "Status": "Success",
                    "Message": "Downloaded"}

        except Exception as e:
            error_msg = str(e)
            if attempt == 1:
                return {"Ticker": ticker,
                        "Name": ticker_name,
                        "Status": "Failed",
                        "Message": error_msg}


# -----------------------------
# Start Download Thread
# -----------------------------
def download_data():

    if not excel_path:
        messagebox.showerror("Error", "Please select Excel file first.")
        return

    start_date = calculate_start_date()
    if start_date is None:
        return

    today_str = datetime.today().strftime("%Y-%m-%d")
    start_str = start_date.strftime("%Y-%m-%d")

    folder_name = "stock_price"
    os.makedirs(folder_name, exist_ok=True)

    ticker_df = pd.read_excel(excel_path)

    if "티커" not in ticker_df.columns or "티커명" not in ticker_df.columns:
        messagebox.showerror("Error", "Excel must contain columns: 티커, 티커명")
        return

    total = len(ticker_df)
    progress_bar["maximum"] = total
    progress_bar["value"] = 0

    results = []

    def run_thread():
        completed = 0

        # CPU 기반 자동 설정
        max_workers = min(32, (os.cpu_count() or 1) + 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(download_with_retry, row, start_str, today_str, folder_name)
                for _, row in ticker_df.iterrows()
            ]

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

                completed += 1
                root.after(0, update_ui, result, completed, total)

        # 로그 저장
        log_df = pd.DataFrame(results)
        log_file = f"download_log_{today_str}.xlsx"
        log_df.to_excel(log_file, index=False)

        root.after(0, lambda: messagebox.showinfo("Completed",
                                                  f"Download Finished!\nLog saved: {log_file}"))

    threading.Thread(target=run_thread).start()


# -----------------------------
# Update UI
# -----------------------------
def update_ui(result, completed, total):
    log_text.insert(tk.END,
                    f"{result['Status']} - {result['Name']} ({result['Ticker']})\n")

    progress_bar["value"] = completed
    percent_label.config(text=f"{int((completed/total)*100)} %")
    root.update_idletasks()


# -----------------------------
# GUI Setup
# -----------------------------
root = tk.Tk()
root.title("Stock Downloader PRO v3")
root.geometry("700x600")

file_button = tk.Button(root, text="Select Excel File", command=select_file)
file_button.pack(pady=10)

period_var = tk.StringVar(value="1 Year")

period_frame = tk.Frame(root)
period_frame.pack(pady=10)

tk.Label(period_frame, text="Select Period:").grid(row=0, column=0)

options = ["1 Year", "3 Years", "10 Years", "Custom"]
period_menu = ttk.Combobox(period_frame, textvariable=period_var,
                           values=options, state="readonly")
period_menu.grid(row=0, column=1)

custom_entry = tk.Entry(period_frame)
custom_entry.grid(row=0, column=2)
custom_entry.insert(0, "YYYY-MM-DD")

download_button = tk.Button(root, text="Start Download", command=download_data)
download_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal",
                               length=600, mode="determinate")
progress_bar.pack(pady=5)

percent_label = tk.Label(root, text="0 %")
percent_label.pack()

log_text = tk.Text(root, height=18)
log_text.pack(pady=10, fill=tk.BOTH, expand=True)

root.mainloop()