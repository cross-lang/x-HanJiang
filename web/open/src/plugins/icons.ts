import type { App, Component } from 'vue'
import {
  ArrowRight,
  Bell,
  Check,
  Close,
  Connection,
  DataAnalysis,
  Delete,
  Document,
  Download,
  Edit,
  Fold,
  Grid,
  Key,
  Link,
  Lock,
  Message,
  Notebook,
  Plus,
  Right,
  Search,
  Setting,
  SwitchButton,
  User,
  UserFilled,
} from '@element-plus/icons-vue'

/**
 * 全局注册的图标白名单。
 * 仅注册模板 / 动态字符串（菜单图标、el-button icon 属性等）需要按名解析的图标，
 * 组件内直接 import 使用的图标不在此列，避免全量注册带来的包体膨胀。
 */
const icons: Record<string, Component> = {
  ArrowRight,
  Bell,
  Check,
  Close,
  Connection,
  DataAnalysis,
  Delete,
  Document,
  Download,
  Edit,
  Fold,
  Grid,
  Key,
  Link,
  Lock,
  Message,
  Notebook,
  Plus,
  Right,
  Search,
  Setting,
  SwitchButton,
  User,
  UserFilled,
}

export function setupIcons(app: App): void {
  for (const [name, component] of Object.entries(icons)) {
    app.component(name, component)
  }
}
