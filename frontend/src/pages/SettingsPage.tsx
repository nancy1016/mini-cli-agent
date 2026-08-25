import { Card, List } from "antd";

import PageHeader from "../components/PageHeader";

const capabilities = [
  "模型服务地址配置",
  "模型名称配置",
  "数据库状态查看",
  "数据备份说明",
];

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="系统设置" description="本阶段保留系统配置入口，不保存任何敏感配置。" />
      <Card title="后续支持能力">
        <List dataSource={capabilities} renderItem={(item) => <List.Item>{item}</List.Item>} />
      </Card>
    </>
  );
}
