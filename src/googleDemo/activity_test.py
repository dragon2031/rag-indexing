"""
Google Drive Activity API 示例
用于查看指定文件夹下的活动记录
使用 Service Account 认证
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from datetime import datetime

# API 权限范围
SCOPES = [
    'https://www.googleapis.com/auth/drive.activity.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

# Service Account 密钥文件路径
SERVICE_ACCOUNT_FILE = 'service-account-key.json'

# 如果需要模拟特定用户（Domain-wide Delegation），设置此邮箱
# 留空则使用 Service Account 本身的身份
DELEGATED_USER_EMAIL = None  # 例如: 'user@yourdomain.com'


def get_credentials():
    """使用 Service Account 获取凭证"""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f'Service Account 密钥文件未找到: {SERVICE_ACCOUNT_FILE}\n'
            f'请从 Google Cloud Console 下载 Service Account JSON 密钥文件'
        )
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    
    # 如果需要模拟特定用户（需要启用 Domain-wide Delegation）
    if DELEGATED_USER_EMAIL:
        credentials = credentials.with_subject(DELEGATED_USER_EMAIL)
    
    return credentials


def format_timestamp(timestamp_str):
    """格式化时间戳"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str


def get_actor_info(actor):
    """提取活动执行者信息"""
    if 'user' in actor:
        return actor['user'].get('knownUser', {}).get('personName', '未知用户')
    elif 'administrator' in actor:
        return '管理员'
    elif 'system' in actor:
        return '系统'
    elif 'anonymous' in actor:
        return '匿名用户'
    return '未知'


def get_action_detail(action):
    """提取活动详情"""
    details = []
    
    if 'detail' in action:
        detail = action['detail']
        
        if 'create' in detail:
            details.append('创建')
        if 'edit' in detail:
            details.append('编辑')
        if 'move' in detail:
            details.append('移动')
        if 'rename' in detail:
            details.append('重命名')
        if 'delete' in detail:
            details.append('删除')
        if 'restore' in detail:
            details.append('恢复')
        if 'permissionChange' in detail:
            details.append('权限变更')
        if 'comment' in detail:
            details.append('评论')
        if 'dlpChange' in detail:
            details.append('DLP变更')
        if 'reference' in detail:
            details.append('引用')
        if 'settingsChange' in detail:
            details.append('设置变更')
    
    return ', '.join(details) if details else '其他活动'


def get_target_info(target):
    """提取目标文件/文件夹信息"""
    if 'driveItem' in target:
        item = target['driveItem']
        name = item.get('name', '未命名')
        title = item.get('title', name)
        mime_type = item.get('mimeType', '未知类型')
        return f"{title} ({mime_type})"
    elif 'drive' in target:
        return f"云端硬盘: {target['drive'].get('title', '未命名')}"
    elif 'fileComment' in target:
        return '文件评论'
    return '未知目标'


def list_folder_activities(folder_id, page_size=10):
    """
    列出指定文件夹下的活动
    
    Args:
        folder_id: Google Drive 文件夹 ID
        page_size: 每页返回的活动数量
    """
    creds = get_credentials()
    service = build('driveactivity', 'v2', credentials=creds)
    
    # 构建查询请求 - 根据官方文档修正
    # ancestorName 用于查询文件夹及其子项的活动
    request_body = {
        'pageSize': page_size,
        'ancestorName': f'items/{folder_id}'
    }
    
    try:
        # 调用 API
        results = service.activity().query(body=request_body).execute()
        activities = results.get('activities', [])
        
        if not activities:
            print(f'文件夹 {folder_id} 没有找到活动记录')
            return
        
        print(f'\n找到 {len(activities)} 条活动记录:\n')
        print('=' * 100)
        
        for idx, activity in enumerate(activities, 1):
            # 时间戳
            timestamp = activity.get('timestamp', '')
            formatted_time = format_timestamp(timestamp)
            
            # 执行者
            actors = activity.get('actors', [])
            actor_names = [get_actor_info(actor) for actor in actors]
            
            # 目标
            targets = activity.get('targets', [])
            target_names = [get_target_info(target) for target in targets]
            
            # 操作
            actions = activity.get('actions', [])
            action_details = [get_action_detail(action) for action in actions]
            
            print(f'\n活动 #{idx}')
            print(f'时间: {formatted_time}')
            print(f'执行者: {", ".join(actor_names)}')
            print(f'操作: {", ".join(action_details)}')
            print(f'目标: {", ".join(target_names)}')
            print('-' * 100)
        
        # 检查是否有更多结果
        next_page_token = results.get('nextPageToken')
        if next_page_token:
            print(f'\n还有更多活动记录。使用 nextPageToken 获取下一页。')
        
    except Exception as e:
        print(f'发生错误: {str(e)}')


def list_folder_activities_with_pagination(folder_id, max_results=50):
    """
    列出指定文件夹下的活动（支持分页）
    
    Args:
        folder_id: Google Drive 文件夹 ID
        max_results: 最多返回的活动数量
    """
    creds = get_credentials()
    service = build('driveactivity', 'v2', credentials=creds)
    
    all_activities = []
    page_token = None
    page_size = 10
    
    try:
        while len(all_activities) < max_results:
            request_body = {
                'pageSize': min(page_size, max_results - len(all_activities)),
                'ancestorName': f'items/{folder_id}'
            }
            
            if page_token:
                request_body['pageToken'] = page_token
            
            results = service.activity().query(body=request_body).execute()
            activities = results.get('activities', [])
            
            if not activities:
                break
            
            all_activities.extend(activities)
            page_token = results.get('nextPageToken')
            
            if not page_token:
                break
        
        print(f'\n总共找到 {len(all_activities)} 条活动记录\n')
        print('=' * 100)
        
        for idx, activity in enumerate(all_activities, 1):
            timestamp = activity.get('timestamp', '')
            formatted_time = format_timestamp(timestamp)
            
            actors = activity.get('actors', [])
            actor_names = [get_actor_info(actor) for actor in actors]
            
            targets = activity.get('targets', [])
            target_names = [get_target_info(target) for target in targets]
            
            actions = activity.get('actions', [])
            action_details = [get_action_detail(action) for action in actions]
            
            print(f'\n活动 #{idx}')
            print(f'时间: {formatted_time}')
            print(f'执行者: {", ".join(actor_names)}')
            print(f'操作: {", ".join(action_details)}')
            print(f'目标: {", ".join(target_names)}')
            print('-' * 100)
            
    except Exception as e:
        print(f'发生错误: {str(e)}')


def list_folder_activities_with_filter(folder_id, page_size=10, filter_str=None):
    """
    列出指定文件夹下的活动（支持自定义过滤器）
    
    Args:
        folder_id: Google Drive 文件夹 ID
        page_size: 每页返回的活动数量
        filter_str: 自定义过滤器字符串（可选）
    """
    creds = get_credentials()
    service = build('driveactivity', 'v2', credentials=creds)
    
    # 构建查询请求
    request_body = {
        'pageSize': page_size,
        'ancestorName': f'items/{folder_id}'
    }
    
    # 添加自定义过滤器
    if filter_str:
        request_body['filter'] = filter_str
    
    try:
        # 调用 API
        results = service.activity().query(body=request_body).execute()
        activities = results.get('activities', [])
        
        if not activities:
            print(f'文件夹 {folder_id} 没有找到活动记录')
            return
        
        print(f'\n找到 {len(activities)} 条活动记录:\n')
        print('=' * 100)
        
        for idx, activity in enumerate(activities, 1):
            timestamp = activity.get('timestamp', '')
            formatted_time = format_timestamp(timestamp)
            
            actors = activity.get('actors', [])
            actor_names = [get_actor_info(actor) for actor in actors]
            
            targets = activity.get('targets', [])
            target_names = [get_target_info(target) for target in targets]
            
            actions = activity.get('actions', [])
            action_details = [get_action_detail(action) for action in actions]
            
            print(f'\n活动 #{idx}')
            print(f'时间: {formatted_time}')
            print(f'执行者: {", ".join(actor_names)}')
            print(f'操作: {", ".join(action_details)}')
            print(f'目标: {", ".join(target_names)}')
            print('-' * 100)
        
        next_page_token = results.get('nextPageToken')
        if next_page_token:
            print(f'\n还有更多活动记录。nextPageToken: {next_page_token}')
        
    except Exception as e:
        print(f'发生错误: {str(e)}')
        import traceback
        traceback.print_exc()


def list_specific_item_activities(item_id, page_size=10):
    """
    列出指定文件或文件夹本身的活动（不包括子项）
    
    Args:
        item_id: Google Drive 文件或文件夹 ID
        page_size: 每页返回的活动数量
    """
    creds = get_credentials()
    service = build('driveactivity', 'v2', credentials=creds)
    
    # 使用 itemName 查询特定项目
    request_body = {
        'pageSize': page_size,
        'itemName': f'items/{item_id}'
    }
    
    try:
        results = service.activity().query(body=request_body).execute()
        activities = results.get('activities', [])
        
        if not activities:
            print(f'项目 {item_id} 没有找到活动记录')
            return
        
        print(f'\n找到 {len(activities)} 条活动记录:\n')
        print('=' * 100)
        
        for idx, activity in enumerate(activities, 1):
            timestamp = activity.get('timestamp', '')
            formatted_time = format_timestamp(timestamp)
            
            actors = activity.get('actors', [])
            actor_names = [get_actor_info(actor) for actor in actors]
            
            targets = activity.get('targets', [])
            target_names = [get_target_info(target) for target in targets]
            
            actions = activity.get('actions', [])
            action_details = [get_action_detail(action) for action in actions]
            
            print(f'\n活动 #{idx}')
            print(f'时间: {formatted_time}')
            print(f'执行者: {", ".join(actor_names)}')
            print(f'操作: {", ".join(action_details)}')
            print(f'目标: {", ".join(target_names)}')
            print('-' * 100)
        
    except Exception as e:
        print(f'发生错误: {str(e)}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 替换为你的文件夹 ID
    # 文件夹 ID 可以从 Google Drive URL 中获取
    # 例如: https://drive.google.com/drive/folders/1ABC123xyz
    # 文件夹 ID 就是 1ABC123xyz
    
    FOLDER_ID = '10SM5DuAT_ijtGdTtjCfikZjV4jXMOh1h'
    
    print('Google Drive Activity API 示例')
    print('=' * 100)
    
    # 方法 1: 获取文件夹及其子项的最近 10 条活动
    print('\n方法 1: 获取文件夹及其子项的最近 10 条活动')
    list_folder_activities(FOLDER_ID, page_size=10)
    
    # 方法 2: 获取最近 50 条活动（支持分页）
    # print('\n方法 2: 获取最近 50 条活动（支持分页）')
    # list_folder_activities_with_pagination(FOLDER_ID, max_results=50)
    
    # 方法 3: 只获取文件夹本身的活动（不包括子项）
    # print('\n方法 3: 只获取文件夹本身的活动')
    # list_specific_item_activities(FOLDER_ID, page_size=10)
    
    # 方法 4: 使用时间过滤器（最近7天）
    # from datetime import timedelta
    # seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
    # time_filter = f'time >= "{seven_days_ago}"'
    # print('\n方法 4: 获取最近7天的活动')
    # list_folder_activities_with_filter(FOLDER_ID, page_size=10, filter_str=time_filter)
