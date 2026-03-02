# ============================================================
# Program Name : stock_downloader_gui_pro_v4.py
# Created Date : 2026-03-01
# Version      : 4.0 (Modern GUI + Treeview + Smart Features)
# Description  : Professional & Interactive Stock Downloader
# ============================================================

import os
import time
import pandas as pd
import FinanceDataReader as fdr
from pykrx import stock
import yfinance as yf
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import subprocess
import certifi
import shutil
import tempfile
import requests
from bs4 import BeautifulSoup
import re

# -----------------------------
# SSL 환경 변수 및 경로 설정 (yfinance/curl_cffi 한글 경로 오류 해결)
# -----------------------------
def setup_secure_cert():
    try:
        # 비-한글 경로(임시 폴더)로 인증서 파일 복사
        root_cert = certifi.where()
        temp_dir = tempfile.gettempdir()
        dest_cert = os.path.join(temp_dir, "python_stock_cacert.pem")
        
        if not os.path.exists(dest_cert):
            shutil.copy2(root_cert, dest_cert)
            
        os.environ['SSL_CERT_FILE'] = dest_cert
        os.environ['REQUESTS_CA_BUNDLE'] = dest_cert
    except:
        pass

setup_secure_cert()

# -----------------------------
# Naver Finance Scraper (Fallback for Domestic)
# -----------------------------
def get_naver_fundamentals(ticker):
    """네이버 금융에서 최신 재무 지표를 크롤링하여 반환"""
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    fundamentals = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # PER, PBR 추출
        per_tag = soup.find('em', id='_per')
        if per_tag: fundamentals['PER'] = per_tag.get_text().replace(',', '')
        
        pbr_tag = soup.find('em', id='_pbr')
        if pbr_tag: fundamentals['PBR'] = pbr_tag.get_text().replace(',', '')
        
        # EPS, BPS 추출 (테이블 내 텍스트 검색)
        aside = soup.find('div', class_='aside_invest_info')
        if aside:
            th_eps = aside.find('th', string=re.compile('EPS'))
            if th_eps:
                td = th_eps.find_next_sibling('td')
                if td: fundamentals['EPS'] = td.get_text().strip().replace(',', '')
                
            th_bps = aside.find('th', string=re.compile('BPS'))
            if th_bps:
                td_bps = th_bps.find_next_sibling('td')
                if td_bps: fundamentals['BPS'] = td_bps.get_text().strip().replace(',', '')

            th_div = aside.find('th', string=re.compile('배당수익률'))
            if th_div:
                td_div = th_div.find_next_sibling('td')
                if td_div: fundamentals['DIV'] = td_div.get_text().strip().replace('%', '')
    except Exception as e:
        print(f"Naver scraping error for {ticker}: {e}")
    return fundamentals

# -----------------------------
# Global Variables
# -----------------------------
excel_path = None
# 기본 저장 폴더를 시스템의 '다운로드' 폴더로 설정
default_save_path = os.path.join(os.path.expanduser("~"), "Downloads")
download_folder = default_save_path
start_time = None

# -----------------------------
# Select Ticker File
# -----------------------------
def select_file():
    global excel_path
    path = filedialog.askopenfilename(
        title="티커 엑셀 파일 선택",
        filetypes=[("Excel Files", "*.xlsx;*.xls"), ("CSV Files", "*.csv")]
    )
    if path:
        excel_path = path
        file_label.config(text=f"선택됨: {os.path.basename(path)}")

# -----------------------------
# Select Save Folder
# -----------------------------
def select_save_folder():
    global download_folder
    folder = filedialog.askdirectory(title="저장 폴더 선택", initialdir=download_folder)
    if folder:
        download_folder = folder
        folder_label.config(text=f"저장처: {os.path.basename(folder) or folder}")

# -----------------------------
# Open Download Folder
# -----------------------------
def open_folder():
    if not os.path.exists(download_folder):
        try:
            os.makedirs(download_folder, exist_ok=True)
        except:
            messagebox.showerror("오류", "폴더를 생성할 수 없습니다.")
            return
    
    if os.name == 'nt': # Windows
        os.startfile(os.path.abspath(download_folder))
    else: # macOS / Linux
        subprocess.run(['open' if os.name == 'posix' else 'xdg-open', os.path.abspath(download_folder)])

# -----------------------------
# Date Calculation
# -----------------------------
def set_period_dates(event=None):
    option = period_var.get()
    today = datetime.today()
    
    if option == "1년":
        start = today - timedelta(days=365)
    elif option == "3년":
        start = today - timedelta(days=365*3)
    elif option == "5년":
        start = today - timedelta(days=365*5)
    elif option == "10년":
        start = today - timedelta(days=365*10)
    else:
        return # Custom은 직접 입력 유지

    start_entry.delete(0, tk.END)
    start_entry.insert(0, start.strftime("%Y-%m-%d"))
    end_entry.delete(0, tk.END)
    end_entry.insert(0, today.strftime("%Y-%m-%d"))

# -----------------------------
# Download Logic (Threaded)
# -----------------------------
def download_with_retry(ticker, ticker_name, start_date, end_date, target_folder):
    """실제 다운로드 및 엑셀 저장 코어"""
    ticker = str(ticker).strip()
    ticker_name = str(ticker_name).strip()
    
    for attempt in range(2): # 1회 재시도 포함
        try:
            # 1. 주가 데이터 가져오기 (FinanceDataReader)
            df = fdr.DataReader(ticker, start=start_date, end=end_date)
            if df.empty:
                return (ticker, ticker_name, "Failed", "No Price Data Found")
            
            # 2. 재무 지표 데이터 가져오기
            # 국내 종목 (숫자 6자리) 확인
            is_korean = ticker.isdigit() and len(ticker) == 6
            
            # 결과 컬럼 초기화 (누락 방지)
            for col in ['BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS', 'DividendYield']:
                if col not in df.columns:
                    df[col] = None

            try:
                if is_korean:
                    # 국내 종목: Naver Finance 크롤링 사용 (pykrx 오류 우회)
                    fund_data = get_naver_fundamentals(ticker)
                    
                    if fund_data:
                        # 추출된 데이터를 모든 행에 상수 값으로 적용
                        for col in ['BPS', 'PER', 'PBR', 'EPS', 'DIV']:
                            if col in fund_data and fund_data[col]:
                                try:
                                    # 숫자로 변환 가능한 경우 변환
                                    val = float(fund_data[col])
                                    df[col] = val
                                except:
                                    df[col] = fund_data[col]
                else:
                    # 해외 종목: yfinance 사용
                    yt = yf.Ticker(ticker)
                    info = yt.info
                    
                    # 주요 지표 추출
                    df['PER'] = info.get('trailingPE')
                    df['PBR'] = info.get('priceToBook')
                    df['EPS'] = info.get('trailingEps')
                    df['BPS'] = info.get('bookValue')
                    df['DividendYield'] = info.get('dividendYield')
            except Exception as fe:
                print(f"Fundamental extraction failed for {ticker}: {fe}")
                pass

            # 파일명 형식: 티커명_시작날짜_종료일자.xlsx
            file_name = f"{ticker_name}_{start_date}_{end_date}.xlsx"
            # 파일명에서 금지된 문자 제거 (윈도우 기준)
            for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                file_name = file_name.replace(char, '')
            
            full_path = os.path.join(target_folder, file_name)
            
            # 특수문자 제거 및 시트명 제한(31자)
            clean_sheet = f"{ticker_name}_{ticker}"[:31]
            df.to_excel(full_path, sheet_name=clean_sheet)
            
            return (ticker, ticker_name, "Success", f"{len(df)}건 완료 (PER/PBR 추가됨)")
        except Exception as e:
            if attempt == 1:
                return (ticker, ticker_name, "Failed", str(e))
            time.sleep(1) # 잠시 대기 후 재시도

def start_download():
    global excel_path, start_time, download_folder
    
    input_mode = mode_var.get()
    start_date = start_entry.get()
    end_date = end_entry.get()
    
    # 다운로드할 대상 리스트 생성 [(티커, 종목명), ...]
    download_list = []

    if input_mode == "file":
        if not excel_path:
            messagebox.showwarning("경고", "먼저 엑셀(티커) 파일을 선택해 주세요.")
            return
        
        try:
            if excel_path.endswith('.csv'):
                ticker_df = pd.read_csv(excel_path)
            else:
                ticker_df = pd.read_excel(excel_path)
                
            t_col = next((c for c in ticker_df.columns if '티커' in c or 'Ticker' in c or 'Symbol' in c), None)
            n_col = next((c for c in ticker_df.columns if '명' in c or 'Name' in c), None)
            
            if not t_col or not n_col:
                messagebox.showerror("오류", "엑셀에 '티커'와 '티커명' 컬럼이 필요합니다.")
                return
            
            for _, row in ticker_df.iterrows():
                download_list.append((str(row[t_col]), str(row[n_col])))
                
        except Exception as e:
            messagebox.showerror("파일 오류", f"파일을 읽을 수 없습니다: {e}")
            return
    else:
        # 직접 입력 모드
        raw_input = direct_entry.get().strip()
        if not raw_input:
            messagebox.showwarning("경고", "다운로드할 티커 정보를 입력해 주세요.\n예: 005930,삼성전자; AAPL,애플")
            return
        
        try:
            # 세미콜론으로 종목 구분, 콤마로 티커/이름 구분
            items = raw_input.split(';')
            for item in items:
                if ',' in item:
                    t, n = item.split(',')
                    download_list.append((t.strip(), n.strip()))
                else:
                    # 이름이 없는 경우 티커를 이름으로 사용
                    t = item.strip()
                    if t: download_list.append((t, t))
            
            if not download_list:
                raise ValueError("형식이 올바르지 않습니다.")
        except Exception:
            messagebox.showerror("입력 오류", "입력 형식이 올바르지 않습니다.\n'티커,종목명' 형식으로 입력해 주세요.\n여러 종목은 세미콜론(;)으로 구분합니다.")
            return

    # 기초 폴더 생성
    os.makedirs(download_folder, exist_ok=True)
    
    # UI 초기화
    for item in tree.get_children():
        tree.delete(item)
    
    progress_bar["maximum"] = len(download_list)
    progress_bar["value"] = 0
    stat_label.config(text="준비 중...", foreground="black")
    download_btn.config(state="disabled")
    start_time = time.time()

    def run_task():
        total = len(download_list)
        success_count = 0
        failed_count = 0
        results_all = []
        
        target_path = download_folder
        max_workers = min(20, (os.cpu_count() or 1) * 2)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(download_with_retry, t, n, start_date, end_date, target_path)
                for t, n in download_list
            ]
            
            for future in as_completed(futures):
                res = future.result()
                ticker, name, status, msg = res
                results_all.append({"Ticker": ticker, "Name": name, "Status": status, "Message": msg})
                
                # UI 업데이트 (메인 스레드 요청)
                root.after(0, update_tree, res)
                
                if status == "Success":
                    success_count += 1
                else:
                    failed_count += 1
                
                # 진행률 업데이트
                current_val = success_count + failed_count
                root.after(0, lambda v=current_val, t=total: update_progress(v, t))

        # 최종 로그 저장
        elapsed = time.time() - start_time
        today_str = datetime.today().strftime("%Y-%m-%d")
        log_file = f"download_summary_{today_str}.xlsx"
        pd.DataFrame(results_all).to_excel(log_file, index=False)
        
        # 완료 메시지
        root.after(0, lambda: finalize_ui(success_count, failed_count, log_file, elapsed))

    threading.Thread(target=run_task, daemon=True).start()

# -----------------------------
# UI Update Helpers
# -----------------------------
def update_tree(res):
    ticker, name, status, msg = res
    tag = "success" if status == "Success" else "fail"
    tree.insert("", tk.END, values=(ticker, name, status, msg), tags=(tag,))
    tree.see(tree.get_children()[-1]) # 자동 스크롤

def update_progress(val, total):
    progress_bar["value"] = val
    percent = int((val / total) * 100)
    percent_label.config(text=f"{percent}% ({val}/{total})")

def finalize_ui(s, f, log, sec):
    download_btn.config(state="normal")
    stat_label.config(
        text=f"완료! 성공: {s}, 실패: {f} (소요시간: {sec:.1f}초)", 
        foreground="#2E7D32" if f == 0 else "#D32F2F"
    )
    messagebox.showinfo("다운로드 완료", f"모든 작업이 완료되었습니다.\n성공: {s}\n실패: {f}\n\n로그 파일: {log}")

def update_log(msg, level="info"):
    # 필요한 경우 별도 로그창에 추가 가능
    pass

# -----------------------------
# Main GUI Setup
# -----------------------------
root = tk.Tk()
root.title("Python Stock Downloader PRO v4.0")
root.geometry("850x700")
root.configure(bg="#F5F5F5")

# Style Configuration
style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview", rowheight=25, font=("Malgun Gothic", 10))
style.configure("Treeview.Heading", font=("Malgun Gothic", 10, "bold"))
style.map("Treeview", background=[('selected', '#B3E5FC')], foreground=[('selected', 'black')])

# Treeview Tags (Coloring)
style.configure("success.Treeview", foreground="#2E7D32")
style.configure("fail.Treeview", foreground="#D32F2F")

# -----------------------------
# UI Interaction
# -----------------------------
def toggle_input_mode():
    mode = mode_var.get()
    if mode == "file":
        btn_file.config(state="normal")
        direct_entry.config(state="disabled")
    else:
        btn_file.config(state="disabled")
        direct_entry.config(state="normal")

# --- Top Area: Setup ---
setup_frame = tk.LabelFrame(root, text=" 1. 입력 방식 및 설정 ", bg="#F5F5F5", font=("Malgun Gothic", 10, "bold"), padx=15, pady=10)
setup_frame.pack(fill="x", padx=20, pady=10)

mode_var = tk.StringVar(value="file")

# 모드 선택 라디오 버튼
mode_frame = tk.Frame(setup_frame, bg="#F5F5F5")
mode_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
ttk.Radiobutton(mode_frame, text="엑셀 파일 이용", variable=mode_var, value="file", command=toggle_input_mode).pack(side="left", padx=5)
ttk.Radiobutton(mode_frame, text="직접 입력", variable=mode_var, value="direct", command=toggle_input_mode).pack(side="left", padx=10)

# 파일 선택 행 (row 1)
btn_file = ttk.Button(setup_frame, text="📁 엑셀/CSV 파일 선택", command=select_file)
btn_file.grid(row=1, column=0, sticky="w", padx=5, pady=2)
file_label = tk.Label(setup_frame, text="파일을 선택해 주세요", bg="#F5F5F5", fg="#666", font=("Malgun Gothic", 9))
file_label.grid(row=1, column=1, sticky="w", padx=10, pady=2)

# 직접 입력 행 (row 2)
tk.Label(setup_frame, text="직접 입력:", bg="#F5F5F5").grid(row=2, column=0, sticky="w", padx=5)
direct_entry = ttk.Entry(setup_frame, width=50)
direct_entry.grid(row=2, column=1, sticky="w", padx=10, pady=2)
direct_entry.insert(0, "005930,삼성전자; NVDA,엔비디아")
direct_entry.config(state="disabled") # 기본은 파일 모드라 비활성화

# 저장 폴더 선택 행 (row 3)
btn_folder = ttk.Button(setup_frame, text="📂 저장 폴더 선택", command=select_save_folder)
btn_folder.grid(row=3, column=0, sticky="w", padx=5, pady=2)
folder_label = tk.Label(setup_frame, text=f"저장처: {os.path.basename(download_folder)}", bg="#F5F5F5", fg="#666", font=("Malgun Gothic", 9))
folder_label.grid(row=3, column=1, sticky="w", padx=10, pady=2)

# --- Period Area ---
period_frame = tk.LabelFrame(root, text=" 2. 기간 설정 ", bg="#F5F5F5", font=("Malgun Gothic", 10, "bold"), padx=15, pady=10)
period_frame.pack(fill="x", padx=20, pady=5)

tk.Label(period_frame, text="조회 기간:", bg="#F5F5F5").grid(row=0, column=0, padx=5)
period_var = tk.StringVar(value="1년")
period_combo = ttk.Combobox(period_frame, textvariable=period_var, values=["1년", "3년", "5년", "10년", "직접입력"], state="readonly", width=10)
period_combo.grid(row=0, column=1, padx=5)
period_combo.bind("<<ComboboxSelected>>", set_period_dates)

tk.Label(period_frame, text="시작일:", bg="#F5F5F5").grid(row=0, column=2, padx=10)
start_entry = ttk.Entry(period_frame, width=12)
start_entry.grid(row=0, column=3)

tk.Label(period_frame, text="종료일:", bg="#F5F5F5").grid(row=0, column=4, padx=10)
end_entry = ttk.Entry(period_frame, width=12)
end_entry.grid(row=0, column=5)

# 초기 날짜 세팅
set_period_dates()

# --- Main Table Area ---
table_frame = tk.Frame(root, bg="#F5F5F5")
table_frame.pack(fill="both", expand=True, padx=20, pady=10)

columns = ("ticker", "name", "status", "message")
tree = ttk.Treeview(table_frame, columns=columns, show="headings")
tree.heading("ticker", text="티커(코드)")
tree.heading("name", text="종목명")
tree.heading("status", text="상태")
tree.heading("message", text="결과 메시지")

tree.column("ticker", width=100, anchor="center")
tree.column("name", width=180, anchor="w")
tree.column("status", width=80, anchor="center")
tree.column("message", width=350, anchor="w")

# Tags for colors
tree.tag_configure("success", foreground="#2E7D32")
tree.tag_configure("fail", foreground="#D32F2F", font=("Malgun Gothic", 10, "bold"))

# Scrollbar for tree
scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# --- Control & Progress Area ---
control_frame = tk.Frame(root, bg="#F5F5F5", pady=10)
control_frame.pack(fill="x", padx=20)

progress_bar = ttk.Progressbar(control_frame, orient="horizontal", mode="determinate")
progress_bar.pack(fill="x", pady=5)

info_frame = tk.Frame(control_frame, bg="#F5F5F5")
info_frame.pack(fill="x")

percent_label = tk.Label(info_frame, text="0% (0/0)", bg="#F5F5F5", font=("Malgun Gothic", 9, "bold"))
percent_label.pack(side="left")

stat_label = tk.Label(info_frame, text="대기 중", bg="#F5F5F5", font=("Malgun Gothic", 9))
stat_label.pack(side="right")

btn_frame = tk.Frame(root, bg="#F5F5F5", pady=15)
btn_frame.pack()

download_btn = tk.Button(
    btn_frame, text="🚀 다운로드 시작", bg="#1976D2", fg="white", 
    font=("Malgun Gothic", 12, "bold"), width=20, height=2, 
    command=start_download, relief="flat", cursor="hand2"
)
download_btn.pack(side="left", padx=10)

folder_btn = tk.Button(
    btn_frame, text="📂 결과 폴더 열기", bg="#455A64", fg="white", 
    font=("Malgun Gothic", 11), width=15, height=2, 
    command=open_folder, relief="flat", cursor="hand2"
)
folder_btn.pack(side="left", padx=10)

# -----------------------------
# Launch
# -----------------------------
root.mainloop()