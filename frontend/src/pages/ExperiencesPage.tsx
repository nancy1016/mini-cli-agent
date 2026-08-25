import { Card, List } from "antd";

import PageHeader from "../components/PageHeader";

const capabilities = [
  "TXT 文件导入",
  "DOCX 文件导入",
  "PDF 文件导入",
  "面试问题提取",
  "薄弱项标记",
  "高频问题分析",
];

export default function ExperiencesPage() {
  return (
    <>
      <PageHeader title="面经管理" description="本阶段仅预留面经模块入口，不提供文件上传。" />
      <Card title="后续支持能力">
        <List dataSource={capabilities} renderItem={(item) => <List.Item>{item}</List.Item>} />
      </Card>
    </>
  );
}
