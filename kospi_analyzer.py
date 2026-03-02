import os
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import glob
import time
import threading

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# 1. 환경 설정
CSV_FILE = 'KOSPI200_with_KSIC_2026.csv'
DATA_DIR = 'data'

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

class KospiAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("코스피 200 수익률 분석기 (Pro버전)")
        self.root.geometry("700x600")
        
        self.df_info = None
        self.is_running = False
        
        self.setup_ui()
        self.check_initial_file()

    def check_initial_file(self):
        """[개선 5] 시작 시 권장 파일 존재 여부 확인 및 안내"""
        if not os.path.exists(CSV_FILE):
            messagebox.showerror(
                "필수 파일 누락", 
                f"'{CSV_FILE}' 파일이 필요합니다.\n\n"
                f"먼저 'kospi200_with_ksic_improved.py'를 실행하여\n"
                f"해당 CSV 파일을 생성해 주세요!"
            )
            self.btn_start_analysis.config(state="disabled")
            self.btn_update_data.config(state="disabled")
        else:
            try:
                self.df_info = pd.read_csv(CSV_FILE)
                self.df_info['종목코드'] = self.df_info['종목코드'].astype(str).str.zfill(6)
                
                # [버그 수정] CSV를 성공적으로 읽어온 '후'에 업종 콤보박스 리스트 업데이트
                sectors = ["전체 업종"]
                if 'KRX_업종' in self.df_info.columns:
                    unique_sectors = sorted([str(s) for s in self.df_info['KRX_업종'].dropna().unique() if str(s) != 'nan'])
                    sectors.extend(unique_sectors)
                self.combo_sector['values'] = sectors
                
            except Exception as e:
                messagebox.showerror("파일 읽기 오류", f"CSV 파일을 읽는 중 오류가 발생했습니다.\n{e}")
                self.btn_start_analysis.config(state="disabled")
                self.btn_update_data.config(state="disabled")

    def setup_ui(self):
        """GUI 화면 구성"""
        # --- 상단: 설정 프레임 ---
        frame_top = ttk.LabelFrame(self.root, text="분석 설정", padding=10)
        frame_top.pack(fill="x", padx=10, pady=10)
        
        # [개선 6] 분석 모드 선택 (최근 일수 vs 날짜 직접 지정)
        self.mode_var = tk.StringVar(value="days")
        
        # 라디오 버튼들을 담을 내부 프레임
        frame_radio = ttk.Frame(frame_top)
        frame_radio.pack(fill="x", pady=(0, 5))
        
        # --- 모드 1: 최근 N일 ---
        ttk.Radiobutton(frame_radio, text="[모드 1] 최근 일수 기준:", variable=self.mode_var, value="days", command=self.toggle_mode).pack(side="left")
        
        # [개선 4 & 추가] 콤보박스와 스핀박스를 결합한 유연한 기간 선택 UI
        self.period_var = tk.IntVar(value=30)
        
        # 자주 쓰는 기간 사전 정의
        self.period_presets = {
            "당일(1일)": 1,
            "1주일(7일)": 7,
            "1개월(30일)": 30,
            "3개월(90일)": 90,
            "반기(180일)": 180,
            "1년(365일)": 365
        }
        
        # 직접 입력 가능한 숫자 칸 (Spinbox)
        self.spin_period = ttk.Spinbox(
            frame_radio, from_=1, to=3650, increment=1, 
            textvariable=self.period_var, width=5, justify="center"
        )
        self.spin_period.pack(side="left", padx=5)
        self.lbl_days = ttk.Label(frame_radio, text="일")
        self.lbl_days.pack(side="left", padx=(0, 20))
        
        ttk.Label(frame_radio, text="빠른 선택:").pack(side="left", padx=(0, 5))
        
        # 드롭다운 메뉴 (Combobox)
        self.combo_period = ttk.Combobox(
            frame_radio, values=list(self.period_presets.keys()), state="readonly", width=15
        )
        self.combo_period.set("1개월(30일)") # 기본 표시값
        self.combo_period.pack(side="left")
        
        # 콤보박스 선택 시 Spinbox(실제 변수) 값 연동
        def on_preset_select(event):
            selected = self.combo_period.get()
            if selected in self.period_presets:
                self.period_var.set(self.period_presets[selected])
                
        self.combo_period.bind("<<ComboboxSelected>>", on_preset_select)
            
        # --- 모드 2: 날짜 지정 ---
        frame_date = ttk.Frame(frame_top)
        frame_date.pack(fill="x", pady=(0, 5))
        
        ttk.Radiobutton(frame_date, text="[모드 2] 직접 날짜 지정:", variable=self.mode_var, value="dates", command=self.toggle_mode).pack(side="left")
        
        # 오늘 날짜를 기본값으로
        today_str = datetime.now().strftime("%Y-%m-%d")
        month_ago_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        self.entry_start_date = ttk.Entry(frame_date, width=12, justify="center")
        self.entry_start_date.insert(0, month_ago_str)
        self.entry_start_date.pack(side="left", padx=5)
        
        ttk.Label(frame_date, text="~").pack(side="left")
        
        self.entry_end_date = ttk.Entry(frame_date, width=12, justify="center")
        self.entry_end_date.insert(0, today_str)
        self.entry_end_date.pack(side="left", padx=5)
        
        ttk.Label(frame_date, text="(형식: YYYY-MM-DD)", foreground="gray").pack(side="left")
        
        # [신규 추가] 특정 KRX 업종만 검색하는 필터링 프레임
        frame_sector = ttk.Frame(frame_top)
        frame_sector.pack(fill="x", pady=(5, 10))
        
        ttk.Label(frame_sector, text="KRX 업종 검색 필터:", font=("", 10, "bold")).pack(side="left", padx=(0, 10))
        
        # 업종 리스트 추출 (CSV 파일에 있는 업종 종류 다 모으기)
        sectors = ["전체 업종"] # 기본값
        if self.df_info is not None and 'KRX_업종' in self.df_info.columns:
            # nan 값 제거하고 순수 업종 이름들만 추출해서 정렬
            unique_sectors = sorted([str(s) for s in self.df_info['KRX_업종'].dropna().unique() if str(s) != 'nan'])
            sectors.extend(unique_sectors)
            
        self.combo_sector = ttk.Combobox(frame_sector, values=sectors, state="readonly", width=25)
        self.combo_sector.set("전체 업종")
        self.combo_sector.pack(side="left")
        
        self.toggle_mode() # 초기 상태 연동
            
        # 버튼들을 나란히 배치하기 위한 프레임
        frame_buttons = ttk.Frame(frame_top)
        frame_buttons.pack(fill="x", pady=5)
        
        # 1. 최신화 버튼
        self.btn_update_data = ttk.Button(frame_buttons, text="데이터 최신화 (1일 1회 권장)", command=self.start_update_thread, width=25)
        self.btn_update_data.pack(side="left", padx=(0, 10), expand=True, anchor="e")
        
        # 2. 분석 부분만 분리한 버튼
        self.btn_start_analysis = ttk.Button(frame_buttons, text="수익률 분석 시작", command=self.start_analysis_thread, width=25)
        self.btn_start_analysis.pack(side="left", expand=True, anchor="w")

        # --- 중간: 결과 출력 프레임 ---
        frame_mid = ttk.LabelFrame(self.root, text="분석 결과", padding=10)
        frame_mid.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.text_result = scrolledtext.ScrolledText(frame_mid, wrap=tk.WORD, font=("Courier", 10))
        self.text_result.pack(fill="both", expand=True)
        
        # --- 하단: 상태 표시 프레임 ---
        frame_bottom = ttk.Frame(self.root)
        frame_bottom.pack(fill="x", padx=10, pady=(0, 10))
        
        self.lbl_status = ttk.Label(frame_bottom, text="대기 중...")
        self.lbl_status.pack(side="left")
        
        # [개선 3] 진행률 바 (Progress Bar)
        self.progress = ttk.Progressbar(frame_bottom, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def toggle_mode(self):
        """라디오 버튼 선택에 따라 입력창 활성/비활성 처리"""
        mode = self.mode_var.get()
        if mode == "days":
            self.spin_period.config(state="normal")
            self.combo_period.config(state="readonly")
            self.lbl_days.config(state="normal") # Ensure label is also enabled/disabled
            self.entry_start_date.config(state="disabled")
            self.entry_end_date.config(state="disabled")
        else:
            self.spin_period.config(state="disabled")
            self.combo_period.config(state="disabled")
            self.lbl_days.config(state="disabled") # Ensure label is also enabled/disabled
            self.entry_start_date.config(state="normal")
            self.entry_end_date.config(state="normal")

    def log(self, text):
        """텍스트 위젯에 메시지 출력"""
        self.text_result.config(state="normal")
        self.text_result.insert(tk.END, text + "\n")
        self.text_result.see(tk.END)
        self.text_result.config(state="disabled")
        self.root.update_idletasks()

    def update_status(self, text):
        """하단 상태 라벨 업데이트"""
        self.lbl_status.config(text=text)
        self.root.update_idletasks()
        
    def disable_buttons(self):
        self.btn_update_data.config(state="disabled")
        self.btn_start_analysis.config(state="disabled")
        
    def enable_buttons(self):
        self.btn_update_data.config(state="normal")
        self.btn_start_analysis.config(state="normal")

    def start_update_thread(self):
        """[기능 분리] 데이터 최신화 스레드 실행"""
        if self.is_running:
            return
            
        self.disable_buttons()
        self.text_result.config(state="normal")
        self.text_result.delete('1.0', tk.END)
        self.text_result.config(state="disabled")
        
        self.is_running = True
        self.progress['value'] = 0
        
        thread = threading.Thread(target=self.run_update_data)
        thread.daemon = True
        thread.start()

    def start_analysis_thread(self):
        """[기능 분리] 데이터 분석 스레드 실행"""
        if self.is_running:
            return
        
        mode = self.mode_var.get()
        period_days = 0
        start_date = None
        end_date = None
        target_sector = self.combo_sector.get() # 새로 추가된 업종 선택값 가져오기
        
        if mode == "days":
            period_days = self.period_var.get()
            if period_days <= 0:
                messagebox.showwarning("입력 오류", "올바른 기간(일수)을 선택하세요.")
                return
        else:
            try:
                # 날짜 형식 검증 (YYYY-MM-DD)
                start_date_str = self.entry_start_date.get()
                end_date_str = self.entry_end_date.get()
                start_date = pd.to_datetime(start_date_str)
                end_date = pd.to_datetime(end_date_str)
                
                if start_date > end_date:
                    messagebox.showwarning("입력 오류", "시작일이 종료일보다 늦을 수 없습니다.")
                    return
            except Exception:
                messagebox.showwarning("입력 오류", "날짜 형식이 올바르지 않습니다.\nYYYY-MM-DD 형식으로 입력해주세요.\n(예: 2026-01-01)")
                return

        self.disable_buttons()
        self.text_result.config(state="normal")
        self.text_result.delete('1.0', tk.END)
        self.text_result.config(state="disabled")
        
        self.is_running = True
        self.progress['value'] = 0
        
        thread = threading.Thread(target=self.run_analyze_data, args=(mode, period_days, start_date, end_date, target_sector))
        thread.daemon = True
        thread.start()

    def run_update_data(self):
        """다운로드 실질 로직"""
        try:
            total_items = len(self.df_info)
            self.progress['maximum'] = total_items
            
            self.log(f">>> 데이터 최신화 확인 및 다운로드 시작... (총 {total_items}종목)")
            
            today_str = datetime.now().strftime("%Y%m%d")
            
            for idx, row in self.df_info.iterrows():
                code, name = row['종목코드'], row['종목명']
                
                # 'nan' 등 잘못된 종목코드는 과감히 건너뛰기
                if pd.isna(code) or str(code).lower() == 'nan':
                    continue
                    
                file_path = f"{DATA_DIR}/{code}.csv"
                
                # [개선 2] 스마트 데이터 (최신 날짜 확인해서 이어 받기)
                need_download = False
                start_date_download = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                end_date_download = today_str
                existing_df = None

                if os.path.exists(file_path):
                    try:
                        existing_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                        if not existing_df.empty:
                            last_date = existing_df.index[-1]
                            # 마지막 기록일 다음날부터 오늘까지 다운로드
                            next_date = last_date + timedelta(days=1)
                            
                            # 만약 오늘보다 빠르다면 추가 다운로드 필요
                            if next_date.date() <= datetime.now().date():
                                start_date_download = next_date.strftime("%Y%m%d")
                                need_download = True
                                # 주말 등 휴장일이라 오늘 날짜까지 비어있어도 요청해봄
                    except Exception:
                        need_download = True # 읽기 실패 시 전체 재다운로드
                else:
                    need_download = True

                if need_download:
                    self.update_status(f"다운로드 중... {name} ({code}) [{start_date_download} ~ {end_date_download}]")
                    try:
                        # [개선 1] 매너 크롤링 (서버 부하 방지용 지연시간)
                        time.sleep(0.3) 
                        
                        new_df = stock.get_market_ohlcv_by_date(start_date_download, end_date_download, code)
                        
                        if not new_df.empty:
                            if existing_df is not None and not existing_df.empty:
                                # 이전 데이터와 합치기
                                combined_df = pd.concat([existing_df, new_df])
                                # 혹시 모를 중복 제거
                                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                                combined_df.to_csv(file_path)
                            else:
                                new_df.to_csv(file_path)
                    except Exception as e:
                        self.log(f"[오류] {name}({code}) 다운로드 실패: {e}")
                
                self.progress['value'] = idx + 1
                
            self.update_status("데이터 업데이트 및 최신화 완료!")
            self.log("\n>>> 데이터 다운로드가 모두 완료되었습니다. '분석 시작' 버튼을 눌러주세요.")
            
        except Exception as e:
            messagebox.showerror("실행 오류", f"업데이트 중 예기치 않은 오류가 발생했습니다.\n{e}")
            self.update_status("오류로 중단됨")
        finally:
            self.is_running = False
            self.enable_buttons()
            self.progress['value'] = 0

    def run_analyze_data(self, mode, period_days, start_date, end_date, target_sector):
        """수익률 표시 실질 로직"""
        try:
            self.progress['maximum'] = 100
            self.progress['value'] = 50
            
            log_msg = f">>> "
            if target_sector != "전체 업종":
                log_msg += f"[{target_sector}-업종만] "
            
            if mode == "days":
                self.log(log_msg + f"최근 {period_days}일 기준 수익률 분석을 시작합니다...")
            else:
                self.log(log_msg + f"지정 기간 [{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}] 수익률 분석을 시작합니다...")
            
            df_returns = self.calculate_returns(mode, period_days, start_date, end_date, target_sector)
            
            if not df_returns.empty:
                self.log("\n" + "="*60)
                if target_sector == "전체 업종":
                    if mode == "days":
                        self.log(f" 🏆 [종목별 누적 수익률 상위 10] (최근 {period_days}일 기준)")
                    else:
                        self.log(f" 🏆 [종목별 누적 수익률 상위 10] (지정 기간)")
                else:
                    self.log(f" 🏆 [{target_sector} 업종] 누적 수익률 순위 (상위 최고 10종목)")
                self.log("="*60)
                top_10 = df_returns.sort_values(by='수익률(%)', ascending=False).head(10)
                # DataFrame 깔끔하게 텍스트 출력
                self.log(top_10.to_string(index=False))
                
                if target_sector == "전체 업종":
                    self.log("\n" + "="*60)
                    self.log(" 🏢 [KRX_업종별 평균 수익률]")
                    self.log("="*60)
                    sector_res = df_returns.groupby('KRX_업종')['수익률(%)'].mean().sort_values(ascending=False)
                    sector_df = pd.DataFrame({'평균 수익률(%)': sector_res.round(2)}).reset_index()
                    self.log(sector_df.to_string(index=False))
                
                if mode == "days":
                    self.update_status(f"분석 완료! (최근 {period_days}일)")
                else:
                    self.update_status("분석 완료! (날짜 지정)")
                self.progress['value'] = 100
            else:
                self.log(f"[안내] 분석 결과가 없습니다. 데이터가 충분한지, 선택한 '{target_sector}' 업종이 맞는지 확인하세요.")
                self.update_status("분석 실패 (데이터 부족 또는 업종 없음)")
            
        except Exception as e:
            messagebox.showerror("분석 오류", f"분석 중 오류가 발생했습니다.\n{e}")
            self.update_status("오류로 중단됨")
        finally:
            self.is_running = False
            self.enable_buttons()

    def calculate_returns(self, mode, period_days, start_date, end_date, target_sector):
        """핵심 수익률 분석 로직"""
        results = []
        
        if mode == "days":
            # 기본 모드: 오늘부터 N일 전
            calc_start_date = pd.Timestamp(datetime.now() - timedelta(days=period_days))
            calc_end_date = pd.Timestamp(datetime.now())
        else:
            # 날짜 지정 모드: 입력받은 시작/종료일
            calc_start_date = pd.Timestamp(start_date)
            calc_end_date = pd.Timestamp(end_date)
        
        for _, row in self.df_info.iterrows():
            code = row['종목코드']
            sector = row.get('KRX_업종', '')
            
            # [기능 2] 특정 업종 필터링 로직 추가
            if pd.isna(code) or str(code).lower() == 'nan':
                continue
                
            # 만약 사용자가 '전체 업종'이 아닌 특정 업종을 골랐고, 현재 주식 업종과 다르면 패스!
            if target_sector != "전체 업종" and str(sector) != target_sector:
                continue
                
            file_path = f"{DATA_DIR}/{code}.csv"
            
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                    
                    # [변경] 지정된 구간(시작일 ~ 종료일) 데이터 필터링 기능 추가
                    df_filtered = df[(df.index >= calc_start_date) & (df.index <= calc_end_date)]
                    
                    if len(df_filtered) >= 1:
                        # 모드에 따라 1건만 있어도(당일 분석) 에러 안 나게 처리
                        start_price = df_filtered.iloc[0]['종가']
                        end_price = df_filtered.iloc[-1]['종가']
                        
                        if start_price > 0: # 0으로 나누기 방지
                            return_rate = ((end_price - start_price) / start_price) * 100
                            
                            results.append({
                                '종목코드': code,
                                '종목명': row['종목명'],
                                'KRX_업종': row['KRX_업종'],
                                '시작일가': int(start_price),
                                '종료일가': int(end_price),
                                '수익률(%)': round(return_rate, 2)
                            })
                except Exception:
                    continue
                    
        return pd.DataFrame(results)

if __name__ == "__main__":
    root = tk.Tk()
    app = KospiAnalyzerApp(root)
    root.mainloop()
