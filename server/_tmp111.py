p = 'src/api/v1/file.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 删上传手写通知
c = c.replace(
    '''    result = service.save_upload(file, folder, operator={"operator_id": current_user.id})

    # 文件上传完成通知（走 dispatcher）
    try:
        from src.api.dependencies import get_notification_dispatcher
        from src.constants.enums import NotificationEvent
        dispatcher = get_notification_dispatcher()
        dispatcher.dispatch_for_user(
            user_id=current_user.id,
            event_type=NotificationEvent.FILE_UPLOADED,
            variables={"filename": file.filename, "folder": folder},
        )
    except Exception:
        pass

    return success_response(result, request, code=201)''',
    '''    result = service.save_upload(file, folder, operator={"operator_id": current_user.id})

    # 文件上传完成通知
    try:
        from src.api.dependencies import get_notification_dispatcher
        from src.constants.enums import NotificationEvent
        get_notification_dispatcher().dispatch_for_user(
            user_id=current_user.id,
            event_type=NotificationEvent.FILE_UPLOADED,
            variables={"filename": file.filename, "folder": folder},
        )
    except Exception:
        pass

    return success_response(result, request, code=201)'''
)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')
