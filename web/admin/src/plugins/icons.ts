import type { App, Component } from 'vue'
import {
  ArrowDown,
  ArrowRight,
  Avatar,
  Back,
  Bell,
  ChatDotRound,
  Check,
  Close,
  Connection,
  DataAnalysis,
  Delete,
  Document,
  Download,
  Folder,
  Grid,
  Link,
  Lock,
  MagicStick,
  Notification,
  Odometer,
  Paperclip,
  Plus,
  Right,
  Search,
  Select,
  Setting,
  Stamp,
  SwitchButton,
  Tickets,
  Upload,
  User,
  UserFilled,
} from '@element-plus/icons-vue'

/**
 * 全局注册的图标白名单。
 * 仅注册模板 / 动态字符串（菜单图标、el-button icon 属性等）需要按名解析的图标，
 * 组件内直接 import 使用的图标不在此列，避免全量注册带来的包体膨胀。
 */
const icons: Record<string, Component> = {
  ArrowDown,
  ArrowRight,
  Avatar,
  Back,
  Bell,
  ChatDotRound,
  Check,
  Close,
  Connection,
  DataAnalysis,
  Delete,
  Document,
  Download,
  Folder,
  Grid,
  Link,
  Lock,
  MagicStick,
  Notification,
  Odometer,
  Paperclip,
  Plus,
  Right,
  Search,
  Select,
  Setting,
  Stamp,
  SwitchButton,
  Tickets,
  Upload,
  User,
  UserFilled,
}

export function setupIcons(app: App): void {
  for (const [name, component] of Object.entries(icons)) {
    app.component(name, component)
  }
}
