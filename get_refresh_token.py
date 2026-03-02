import os
from google_auth_oauthlib.flow import InstalledAppFlow

# 구글 드라이브 접근 권한 범위
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    if not os.path.exists('client_secret.json'):
        print("❌ 'client_secret.json' 파일이 없습니다. 가이드에 따라 먼저 다운로드해 주세요.")
        return

    # 로컬 서버를 사용하여 인증을 진행합니다. (Google 보안 정책상 이 방식이 가장 권장됩니다.)
    # prompt='consent'와 access_type='offline'을 설정하여 Refresh Token을 발급받습니다.
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    
    print("\n" + "="*50)
    print("📢 잠시 후 브라우저 창이 자동으로 열립니다.")
    print("만약 열리지 않는다면 터미널에 나타나는 URL을 직접 클릭해 주세요.")
    print("="*50)

    # port=0은 사용 가능한 임의의 포트를 자동으로 선택합니다.
    creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')

    print("\n" + "="*50)
    print("✅ 인증 성공! 아래 정보를 복사해서 저에게 알려주세요.")
    print("="*50)
    print(f"CLIENT_ID: {creds.client_id}")
    print(f"CLIENT_SECRET: {creds.client_secret}")
    print(f"REFRESH_TOKEN: {creds.refresh_token}")
    print("="*50)

if __name__ == '__main__':
    main()
