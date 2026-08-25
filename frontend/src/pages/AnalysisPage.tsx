import { Card, List } from "antd";

import PageHeader from "../components/PageHeader";

const capabilities = [
  "面经总数统计",
  "问题分类统计",
  "高频问题统计",
  "薄弱项统计",
  "最近新增问题",
];

export default function AnalysisPage() {
  return (
    <>
      <PageHeader title="分析中心" description="数据分析能力将在面经数据闭环建立后接入。" />
      <Card title="后续支持能力">
        <List dataSource={capabilities} renderItem={(item) => <List.Item>{item}</List.Item>} />
      </Card>
    </>
  );
}
