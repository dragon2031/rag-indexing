"""
Google Drive API - 获取指定文件夹下所有文件的 ID 和 MD5 checksum
支持两种认证方式：
1. Service Account 认证（适合服务器端应用）
2. OAuth 2.0 用户认证（适合个人使用）

支持定时轮询模式：每30秒自动查询一次
"""

from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import csv
import os
import pickle
import threading
import time
import json
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def save_token_as_json(creds, filename='token.json'):
    """将 token 保存为 JSON 格式并打印"""
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes,
    }
    
    if hasattr(creds, 'expiry') and creds.expiry:
        token_data['expiry'] = creds.expiry.isoformat()
    
    # 保存到文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)
    
    # 打印 token 内容
    print('\n' + '='*70)
    print(f'📄 Token 已保存到: {filename}')
    print('='*70)
    print(json.dumps(token_data, indent=2, ensure_ascii=False))
    print('='*70 + '\n')


# 认证方式配置
# 可选值: 'service_account' 或 'oauth'
AUTH_METHOD = 'oauth'  # 默认使用 OAuth 2.0 认证

# Service Account 配置
SERVICE_ACCOUNT_FILE = 'service-account-key.json'

# OAuth 2.0 配置
OAUTH_CREDENTIALS_FILE = 'credentials.json'
OAUTH_TOKEN_FILE = 'token.pickle'
TOKEN_JSON_FILE = 'token.json'  # 用于保存 JSON 格式的 token


def get_credentials_oauth():
    """使用 OAuth 2.0 获取用户凭证"""
    creds = None
    
    if os.path.exists(OAUTH_TOKEN_FILE):
        with open(OAUTH_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print('刷新访问令牌...')
            creds.refresh(Request())
        else:
            if not os.path.exists(OAUTH_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f'OAuth 客户端密钥文件未找到: {OAUTH_CREDENTIALS_FILE}\n'
                    f'请从 Google Cloud Console 下载 OAuth 2.0 客户端 ID JSON 文件'
                )
            
            print('开始 OAuth 2.0 授权流程...')
            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CREDENTIALS_FILE, SCOPES
            )
            
            # 使用控制台模式，适合无头服务器
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print('\n' + '='*70)
            print('请在浏览器中打开以下 URL 进行授权：')
            print(auth_url)
            print('='*70)
            print('\n授权后，Google 会显示一个授权码')
            
            code = input('请将授权码粘贴到这里: ').strip()
            
            flow.fetch_token(code=code)
            creds = flow.credentials
            print('授权成功！')
        
        with open(OAUTH_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        
        # 保存并打印 JSON 格式的 token
        save_token_as_json(creds, TOKEN_JSON_FILE)
    
    return creds


def get_credentials_service_account():
    """使用 Service Account 获取凭证"""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f'Service Account 密钥文件未找到: {SERVICE_ACCOUNT_FILE}'
        )
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return creds


def get_credentials():
    """根据配置选择认证方式"""
    if AUTH_METHOD == 'oauth':
        print(f'使用 OAuth 2.0 用户认证')
        return get_credentials_oauth()
    elif AUTH_METHOD == 'service_account':
        print(f'使用 Service Account 认证')
        return get_credentials_service_account()
    else:
        raise ValueError(f'不支持的认证方式: {AUTH_METHOD}')


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


def export_to_csv(files, filename='drive_files.csv'):
    """导出文件列表到 CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['id', 'name', 'md5Checksum'])
        writer.writeheader()
        for f in files:
            writer.writerow({
                'id': f['id'],
                'name': f['name'],
                'md5Checksum': f.get('md5Checksum', 'N/A')
            })


class DriveMonitor:
    """Google Drive 文件夹监控器 - 定时轮询"""
    
    def __init__(self, service, folder_id, interval=30):
        """
        初始化监控器
        
        Args:
            service: Google Drive API service 对象
            folder_id: 要监控的文件夹 ID
            interval: 轮询间隔（秒），默认 30 秒
        """
        self.service = service
        self.folder_id = folder_id
        self.interval = interval
        self.running = False
        self.thread = None
        self.last_files = {}
        self.poll_count = 0
    
    def _monitor_loop(self):
        """监控循环（在后台线程中运行）"""
        print(f'🚀 监控线程已启动，每 {self.interval} 秒查询一次')
        print(f'📁 监控文件夹: {self.folder_id}')
        print('按 Ctrl+C 停止监控\n')
        
        while self.running:
            try:
                self.poll_count += 1
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                print(f'[{timestamp}] 🔍 第 {self.poll_count} 次查询...')
                
                # 调用 get_all_files
                files = get_all_files(self.service, self.folder_id)
                
                # 检测变化
                current_files = {f['id']: f for f in files}
                changes = self._detect_changes(current_files)
                
                print(f'[{timestamp}] ✅ 找到 {len(files)} 个文件')
                
                if changes:
                    self._print_changes(changes)
                else:
                    print(f'[{timestamp}] 📊 无变化')
                
                # 导出到 CSV
                export_to_csv(files)
                
                # 更新缓存
                self.last_files = current_files
                
                print(f'[{timestamp}] 💾 已导出到 drive_files.csv')
                print('-' * 70)
                
                # 等待下一次轮询
                time.sleep(self.interval)
                
            except Exception as e:
                print(f'❌ 查询出错: {e}')
                print(f'⏳ {self.interval} 秒后重试...\n')
                time.sleep(self.interval)
    
    def _detect_changes(self, current_files):
        """检测文件变化"""
        if not self.last_files:
            return None
        
        changes = {
            'added': [],
            'removed': [],
            'modified': []
        }
        
        # 检测新增和修改
        for file_id, file_info in current_files.items():
            if file_id not in self.last_files:
                changes['added'].append(file_info)
            else:
                old_info = self.last_files[file_id]
                if (file_info.get('name') != old_info.get('name') or 
                    file_info.get('md5Checksum') != old_info.get('md5Checksum')):
                    changes['modified'].append(file_info)
        
        # 检测删除
        for file_id, file_info in self.last_files.items():
            if file_id not in current_files:
                changes['removed'].append(file_info)
        
        # 如果没有任何变化，返回 None
        if not any(changes.values()):
            return None
        
        return changes
    
    def _print_changes(self, changes):
        """打印变化信息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if changes['added']:
            print(f'[{timestamp}] ➕ 新增 {len(changes["added"])} 个文件:')
            for f in changes['added']:
                print(f'   + {f["name"]}')
        
        if changes['removed']:
            print(f'[{timestamp}] ➖ 删除 {len(changes["removed"])} 个文件:')
            for f in changes['removed']:
                print(f'   - {f["name"]}')
        
        if changes['modified']:
            print(f'[{timestamp}] 📝 修改 {len(changes["modified"])} 个文件:')
            for f in changes['modified']:
                print(f'   ~ {f["name"]}')
    
    def start(self):
        """启动监控"""
        if self.running:
            print('⚠️  监控已在运行中')
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止监控"""
        if not self.running:
            return
        
        print('\n🛑 正在停止监控...')
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print('✅ 监控已停止')
    
    def wait(self):
        """等待监控线程结束（阻塞主线程）"""
        if self.thread:
            try:
                self.thread.join()
            except KeyboardInterrupt:
                self.stop()


def run_once(folder_id):
    """单次运行模式"""
    print(f'认证方式: {AUTH_METHOD}')
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    print(f'查询文件夹: {folder_id}')
    
    # 获取所有文件
    files = get_all_files(service, folder_id)
    
    print(f'找到 {len(files)} 个文件\n')
    
    # 打印结果
    for f in files:
        md5 = f.get('md5Checksum', 'N/A')
        print(f"{f['name']:<40} ID: {f['id']:<35} MD5: {md5}")
    
    # 导出 CSV
    export_to_csv(files)
    print(f'\n已导出到 drive_files.csv')


def run_monitor(folder_id, interval=30):
    """监控模式 - 定时轮询"""
    print(f'认证方式: {AUTH_METHOD}')
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    # 创建并启动监控器
    monitor = DriveMonitor(service, folder_id, interval)
    monitor.start()
    
    # 等待监控线程（会阻塞直到 Ctrl+C）
    monitor.wait()


if __name__ == '__main__':
    FOLDER_ID = '10SM5DuAT_ijtGdTtjCfikZjV4jXMOh1h'
    
    # 运行模式选择
    # 'once' - 单次运行
    # 'monitor' - 监控模式（每30秒轮询一次）
    MODE = 'monitor'  # 改为 'once' 可切换到单次运行模式
    INTERVAL = 30  # 轮询间隔（秒）
    
    try:
        if MODE == 'monitor':
            print('='*70)
            print('🔄 监控模式')
            print('='*70)
            run_monitor(FOLDER_ID, INTERVAL)
        else:
            print('='*70)
            print('📋 单次运行模式')
            print('='*70)
            run_once(FOLDER_ID)
        
    except KeyboardInterrupt:
        print('\n\n👋 用户中断')
    except Exception as e:
        print(f'❌ 错误: {e}')
