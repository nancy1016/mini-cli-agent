import { Card, List } from "antd";

import PageHeader from "../components/PageHeader";

const capabilities = [
  "自然语言新增投递",
  "自然语言修改投递字段",
  "自然语言更新状态",
  "自然语言新增面试",
  "查询投递和面试",
  "导入后辅助解析面经",
];

export default function AgentPage() {
  return (
    <>
      <PageHeader title="Agent 助手" description="Web 对话入口将在后续里程碑接入。" />
      <Card title="后续支持能力">
        <List dataSource={capabilities} renderItem={(item) => <List.Item>{item}</List.Item>} />
      </Card>
    </>
  );
}
