p = 'src/services/file_service.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. save_upload 里加上传通知
c = c.replace(
    '''        logger.info(
            f"File uploaded: key={result.key} size={result.size} "
            f"operator_id={uploaded_by} file_id={entity.id}"
        )''',
    '''        logger.info(
            f"File uploaded: key={result.key} size={result.size} "
            f"operator_id={uploaded_by} file_id={entity.id}"
        )

        # 文件上传完成通知
        if uploaded_by:
            try:
                from src.api.dependencies import get_notification_dispatcher
                from src.constants.enums import NotificationEvent
                get_notification_dispatcher().dispatch_for_user(
                    user_id=uploaded_by,
                    event_type=NotificationEvent.FILE_UPLOADED,
                    variables={"filename": file_name, "folder": folder},
                )
            except Exception:
                pass'''
)

# 2. delete_file 里加删除通知
c = c.replace(
    '''    def delete_file(self, file_id: int) -> bool:''',
    '''    def delete_file(self, file_id: int, operator_username: str = "") -> bool:
        # 先查文件信息（拿上传者和文件名）
        f = self._session.query(FileEntity).filter(FileEntity.id == file_id).first()'''
)

# 找到 delete_file 的 return 前面加通知
import re
# 先看看 delete_file 完整代码
print("check delete_file")
