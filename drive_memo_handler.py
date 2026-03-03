import streamlit as st
import io
import os
import time
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2.credentials import Credentials

@st.cache_resource
def _get_cached_drive_service(creds_dict_json):
    """인증 정보를 기반으로 드라이브 서비스 객체를 캐싱하여 생성합니다."""
    try:
        creds_dict = json.loads(creds_dict_json)
        creds = Credentials.from_authorized_user_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive.file'])
        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        st.error(f"구글 서비스 생성 중 오류: {e}")
        return None

@st.cache_data(ttl=300)
def _load_memo_content(folder_id, file_name, creds_json):
    """구글 드라이브에서 메모 내용을 불러옵니다 (모듈 레벨 캐싱)."""
    if not creds_json: return ""
    
    try:
        service = _get_cached_drive_service(creds_json)
        if not service: return ""
        
        query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        
        if not files: return ""
            
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        return fh.read().decode('utf-8')
    except Exception as e:
        return f"내용을 불러오지 못했습니다: {str(e)}"

class DriveMemoHandler:
    def __init__(self, folder_id, cache_dir=".cache"):
        self.folder_id = folder_id
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def get_creds_dict_json(self):
        """인증 정보를 JSON 문자열로 반환합니다."""
        try:
            if 'google_drive' not in st.secrets: return None
            creds_info = st.secrets["google_drive"]
            return json.dumps({
                "client_id": creds_info.get("client_id"),
                "client_secret": creds_info.get("client_secret"),
                "refresh_token": creds_info.get("refresh_token"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
        except: return None

    def get_drive_service(self):
        """인증된 드라이브 서비스 객체를 반환합니다."""
        creds_json = self.get_creds_dict_json()
        if creds_json:
            return _get_cached_drive_service(creds_json)
        return None

    def upload_file(self, file_name, content_buffer, mime_type="text/plain"):
        """파일을 드라이브에 업로드하거나 업데이트합니다."""
        service = self.get_drive_service()
        if not service: return False

        try:
            query = f"name = '{file_name}' and '{self.folder_id}' in parents and trashed = false"
            results = service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            media = MediaIoBaseUpload(content_buffer, mimetype=mime_type, resumable=False)
            
            if files:
                service.files().update(fileId=files[0]['id'], media_body=media).execute()
            else:
                metadata = {'name': file_name, 'parents': [self.folder_id]}
                service.files().create(body=metadata, media_body=media, fields='id').execute()
            
            # 업로드 성공 시 캐시 초기화
            _load_memo_content.clear(self.folder_id, file_name, self.get_creds_dict_json())
            self._clear_list_cache()
            return True
        except Exception:
            return False

    def list_files(self):
        """폴더 내의 텍스트 파일 목록을 가져옵니다."""
        creds_json = self.get_creds_dict_json()
        if not creds_json: return []
        return self._get_cached_list(creds_json, self.folder_id)

    @st.cache_data(ttl=600)
    def _get_cached_list(creds_json, folder_id):
        try:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_authorized_user_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive.file'])
            service = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            query = f"'{folder_id}' in parents and trashed = false and mimeType = 'text/plain'"
            results = service.files().list(q=query, fields="files(name)").execute()
            return sorted([f['name'] for f in results.get('files', [])])
        except: return []

    def _clear_list_cache(self):
        """파일 목록 캐시를 초기화합니다."""
        DriveMemoHandler._get_cached_list.clear()

    def delete_file(self, file_name, protected_file):
        """파일을 휴지통으로 보냅니다."""
        if file_name == protected_file: return False
        service = self.get_drive_service()
        if not service: return False
        try:
            query = f"name = '{file_name}' and '{self.folder_id}' in parents and trashed = false"
            results = service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            if files:
                service.files().update(fileId=files[0]['id'], body={'trashed': True}).execute()
                self._clear_list_cache()
                return True
            return False
        except: return False

def show_memo_ui(folder_id, default_file="dashboard_memo.txt"):
    """메모 기능 UI를 렌더링하는 통합 함수입니다."""
    handler = DriveMemoHandler(folder_id)
    creds_json = handler.get_creds_dict_json()
    
    if not creds_json:
        st.error("구글 드라이브 인증 정보를 `secrets.toml`에서 찾을 수 없습니다.")
        return

    # 1. 파일 목록 가져오기
    files = handler.list_files()
    if default_file not in files: files.insert(0, default_file)

    # 2. 세션 상태 초기화
    if 'active_memo_file' not in st.session_state:
        st.session_state.active_memo_file = default_file

    if 'memo_content' not in st.session_state:
        with st.spinner("메모 불러오는 중..."):
            st.session_state.memo_content = _load_memo_content(folder_id, st.session_state.active_memo_file, creds_json)

    # 3. UI 렌더링
    with st.expander("📝 개인 메모 (구글 드라이브 연동)", expanded=False):
        col_list, col_btn = st.columns([7, 3])
        
        with col_list:
            sel_file = st.selectbox("파일 선택", options=files, 
                                   index=files.index(st.session_state.active_memo_file) if st.session_state.active_memo_file in files else 0,
                                   label_visibility="collapsed")
        with col_btn:
            if st.button("📥 불러오기", use_container_width=True):
                st.session_state.active_memo_file = sel_file
                _load_memo_content.clear(folder_id, sel_file, creds_json)
                st.session_state.memo_content = _load_memo_content(folder_id, sel_file, creds_json)
                st.rerun()

        st.caption(f"현재 편집 중: `{st.session_state.active_memo_file}`")
        # 텍스트 에리어의 변경 사항을 바로 세션 상태에 반영하기 위해 key를 지정할 수도 있지만, 
        # 여기서는 기존 방식대로 value와 저장 시점의 값을 사용합니다.
        new_content = st.text_area("내용", value=st.session_state.memo_content, height=200, label_visibility="collapsed")
        
        c1, c2, c3 = st.columns([4, 4, 2])
        with c1:
            if st.button("💾 저장", use_container_width=True):
                with st.spinner("저장 중..."):
                    if handler.upload_file(st.session_state.active_memo_file, io.BytesIO(new_content.encode('utf-8'))):
                        st.success("저장 완료!")
                        st.session_state.memo_content = new_content
                        # 저장 후 로드 캐시 초기화는 upload_file 내부에서 처리함
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("저장에 실패했습니다.")
        with c2:
            with st.popover("📁 다른 이름 저장", use_container_width=True):
                new_name = st.text_input("새 파일명", value="새_메모.txt")
                if st.button("확인", key="memo_save_as_btn"):
                    if not new_name.endswith(".txt"): new_name += ".txt"
                    if handler.upload_file(new_name, io.BytesIO(new_content.encode('utf-8'))):
                        st.success("생성 완료!")
                        st.session_state.active_memo_file = new_name
                        st.session_state.memo_content = new_content
                        time.sleep(0.5)
                        st.rerun()
        with c3:
            if st.session_state.active_memo_file == default_file:
                st.button("🗑️", disabled=True, use_container_width=True)
            else:
                with st.popover("🗑️", use_container_width=True):
                    st.warning("삭제하시겠습니까?")
                    if st.button("확인", type="primary", use_container_width=True):
                        if handler.delete_file(st.session_state.active_memo_file, default_file):
                            st.session_state.active_memo_file = default_file
                            _load_memo_content.clear(folder_id, default_file, creds_json)
                            st.session_state.memo_content = _load_memo_content(folder_id, default_file, creds_json)
                            st.rerun()
