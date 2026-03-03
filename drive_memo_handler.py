import streamlit as st
import io
import os
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2.credentials import Credentials

@st.cache_resource
def _get_cached_drive_service(creds_dict_json):
    """인증 정보를 기반으로 드라이브 서비스 객체를 캐싱하여 생성합니다."""
    import json
    from google.oauth2.credentials import Credentials
    creds_dict = json.loads(creds_dict_json)
    creds = Credentials.from_authorized_user_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive.file'])
    return build('drive', 'v3', credentials=creds, cache_discovery=False)

class DriveMemoHandler:
    def __init__(self, folder_id, cache_dir=".cache"):
        self.folder_id = folder_id
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def get_creds_dict_json(self):
        """인증 정보를 JSON 문자열로 반환합니다 (캐싱 키로 사용)."""
        try:
            if 'google_drive' not in st.secrets: return None
            creds_info = st.secrets["google_drive"]
            import json
            return json.dumps({
                "client_id": creds_info.get("client_id"),
                "client_secret": creds_info.get("client_secret"),
                "refresh_token": creds_info.get("refresh_token"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
        except: return None

    def get_drive_service(self):
        """캐싱된 구글 드라이브 서비스 객체를 반환합니다."""
        creds_json = self.get_creds_dict_json()
        if creds_json:
            return _get_cached_drive_service(creds_json)
        return None

    def download_file(self, file_name, use_cache=False, service=None):
        """드라이브에서 파일을 다운로드합니다."""
        local_path = os.path.join(self.cache_dir, file_name)
        if use_cache and os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                return io.BytesIO(f.read())

        if not service:
            service = self.get_drive_service()
        if not service: return None

        try:
            query = f"name = '{file_name}' and '{self.folder_id}' in parents and trashed = false"
            results = service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            if not files: return None
                
            file_id = files[0]['id']
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            with open(local_path, 'wb') as f:
                f.write(fh.read())
            fh.seek(0)
            return fh
        except: return None

    def upload_file(self, file_name, content_buffer, mime_type="text/plain", service=None):
        """파일을 드라이브에 업로드하거나 업데이트합니다."""
        if not service:
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
            
            # 업로드 성공 시 목록 캐시 초기화
            self._clear_list_cache()
            return True
        except Exception as e:
            return False

    def list_files(self, service=None):
        """폴더 내의 텍스트 파일 목록을 가져옵니다 (캐싱 적용)."""
        creds_json = self.get_creds_dict_json()
        if not creds_json: return []
        return self._get_cached_list(creds_json, self.folder_id, service=service)

    @st.cache_data(ttl=600)
    def _get_cached_list(_self, creds_json, folder_id, service=None):
        if not service:
            service = _self.get_drive_service()
        if not service: return []
        try:
            query = f"'{folder_id}' in parents and trashed = false and mimeType = 'text/plain'"
            results = service.files().list(q=query, fields="files(name)").execute()
            return sorted([f['name'] for f in results.get('files', [])])
        except: return []

    def _clear_list_cache(self):
        """파일 목록 캐시를 강제로 초기화합니다."""
        self._get_cached_list.clear()

    def delete_file(self, file_name, protected_file, service=None):
        """파일을 휴지통으로 보냅니다."""
        if file_name == protected_file:
            return False
            
        if not service:
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
        except:
            return False

def show_memo_ui(folder_id, default_file="dashboard_memo.txt"):
    """메모 기능 UI를 렌더링하는 통합 함수입니다."""
    handler = DriveMemoHandler(folder_id)
    
    # 캐시된 로드 함수
    @st.cache_data(ttl=300)
    def _cached_load(fname):
        buf = handler.download_file(fname, use_cache=False)
        return buf.read().decode('utf-8') if buf else ""

    if 'active_memo_file' not in st.session_state:
        st.session_state.active_memo_file = default_file

    if 'memo_content' not in st.session_state:
        st.session_state.memo_content = _cached_load(st.session_state.active_memo_file)

    with st.expander("📝 개인 메모 (구글 드라이브 연동)", expanded=False):
        col_list, col_btn = st.columns([7, 3])
        files = handler.list_files()
        if default_file not in files: files.insert(0, default_file)
        
        with col_list:
            sel_file = st.selectbox("파일 선택", options=files, 
                                   index=files.index(st.session_state.active_memo_file) if st.session_state.active_memo_file in files else 0,
                                   label_visibility="collapsed")
        with col_btn:
            if st.button("📥 불러오기", use_container_width=True):
                st.session_state.active_memo_file = sel_file
                _cached_load.clear()
                st.session_state.memo_content = _cached_load(sel_file)
                st.rerun()

        st.caption(f"현재 편집 중: `{st.session_state.active_memo_file}`")
        new_content = st.text_area("내용", value=st.session_state.memo_content, height=200, label_visibility="collapsed")
        
        c1, c2, c3 = st.columns([4, 4, 2])
        with c1:
            if st.button("💾 저장", use_container_width=True):
                with st.spinner("저장 중..."):
                    if handler.upload_file(st.session_state.active_memo_file, io.BytesIO(new_content.encode('utf-8'))):
                        st.success("저장 완료!")
                        st.session_state.memo_content = new_content
                        _cached_load.clear()
                        time.sleep(1)
                        st.rerun()
        with c2:
            with st.popover("📁 다른 이름 저장", use_container_width=True):
                new_name = st.text_input("새 파일명", value="새_메모.txt")
                if st.button("확인", key="memo_save_as_btn"):
                    if not new_name.endswith(".txt"): new_name += ".txt"
                    if handler.upload_file(new_name, io.BytesIO(new_content.encode('utf-8'))):
                        st.success("생성 완료!")
                        st.session_state.active_memo_file = new_name
                        st.session_state.memo_content = new_content
                        _cached_load.clear()
                        time.sleep(1)
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
                            _cached_load.clear()
                            st.session_state.memo_content = _cached_load(default_file)
                            st.rerun()
