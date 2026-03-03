import streamlit as st
import io
import os
from drive_memo_handler import DriveMemoHandler

# 테스트용 폴더 ID (사용자의 코드에서 가져옴)
FOLDER_ID = '1nv9imwPebStoOVJFWM5U6HIvAkib5xRY'
CACHE_DIR = 'test_cache'
TEST_FILE = 'test_download.txt'

def test_handler():
    handler = DriveMemoHandler(FOLDER_ID, cache_dir=CACHE_DIR)
    
    print("1. 인증 정보 확인 중...")
    creds = handler.get_creds_dict_json()
    if not creds:
        print("❌ 인증 정보를 찾을 수 없습니다. secrets.toml을 확인하세요.")
        return

    print("2. 테스트 파일 업로드 시도...")
    content = b"Hello, Antigravity download test!"
    buffer = io.BytesIO(content)
    if handler.upload_file(TEST_FILE, buffer, mime_type="text/plain"):
        print(f"✅ {TEST_FILE} 업로드 성공")
    else:
        print("❌ 업로드 실패")
        return

    print("3. download_file 메서드 테스트...")
    downloaded_buffer = handler.download_file(TEST_FILE, use_cache=False)
    if downloaded_buffer:
        downloaded_content = downloaded_buffer.read()
        print(f"✅ 다운로드 성공: {downloaded_content}")
        if downloaded_content == content:
            print("✨ 데이터 일치 확인!")
        else:
            print("⚠️ 데이터 불일치!")
    else:
        print("❌ 다운로드 실패 (메서드 확인 필요)")

    # 캐시 확인
    cache_path = os.path.join(CACHE_DIR, TEST_FILE)
    if os.path.exists(cache_path):
        print(f"✅ 로컬 캐시 파일 생성 확인: {cache_path}")
    else:
        print("❌ 로컬 캐시 파일이 생성되지 않았습니다.")

if __name__ == "__main__":
    # Streamlit 환경이 아니므로 st.secrets를 모방하거나 
    # 실제 환경에서 실행하기 위해 안내합니다.
    print("이 테스트는 Streamlit secrets가 설정된 환경에서 실행되어야 합니다.")
    try:
        test_handler()
    except Exception as e:
        print(f"오류 발생: {e}")
