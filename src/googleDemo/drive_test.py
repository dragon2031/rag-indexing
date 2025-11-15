"""
Google Drive API - 获取指定文件夹下所有文件的 ID 和 MD5 checksum
使用 Service Account 认证
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import csv

SERVICE_ACCOUNT_FILE = 'service-account-key.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_credentials():
    """获取 Service Account 凭证"""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return creds


def get_all_files(service, folder_id):
    """一次性获取文件夹下所有文件（包括子文件夹）"""
    all_files = []
    page_token = None
    
    # 使用 'in parents' 查询，自动包含所有子文件夹内容
    query = f"'{folder_id}' in parents and trashed=false"
    
    while True:
        results = service.files().list(
            q=query,
            pageSize=1000,
            fields="nextPageToken, files(id, name, md5Checksum)",
            pageToken=page_token
        ).execute()
        
        files = results.get('files', [])
        all_files.extend(files)
        
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    
    return all_files


if __name__ == '__main__':
    FOLDER_ID = '10SM5DuAT_ijtGdTtjCfikZjV4jXMOh1h'
    
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        print(f'查询文件夹: {FOLDER_ID}')
        
        # 获取所有文件
        files = get_all_files(service, FOLDER_ID)
        
        print(f'找到 {len(files)} 个文件\n')
        
        # 打印结果
        for f in files:
            md5 = f.get('md5Checksum', 'N/A')
            print(f"{f['name']:<40} ID: {f['id']:<35} MD5: {md5}")
        
        # 导出 CSV
        with open('drive_files.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['id', 'name', 'md5Checksum'])
            writer.writeheader()
            for f in files:
                writer.writerow({
                    'id': f['id'],
                    'name': f['name'],
                    'md5Checksum': f.get('md5Checksum', 'N/A')
                })
        
        print(f'\n已导出到 drive_files.csv')
        
    except Exception as e:
        print(f'错误: {e}')
