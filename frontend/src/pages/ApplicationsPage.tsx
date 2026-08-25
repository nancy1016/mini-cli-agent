import { useEffect, useState } from "react";
import { Input, Select, Space, Spin, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";

import { getApplications, type ApplicationRecord } from "../api/applications";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";

const columns: ColumnsType<ApplicationRecord> = [
  { title: "公司", dataIndex: "company", fixed: "left", width: 180 },
  { title: "岗位", dataIndex: "position", width: 150 },
  { title: "地点", dataIndex: "location", width: 100, render: (value) => value || "—" },
  { title: "招聘类型", dataIndex: "recruit_type", width: 110, render: (value) => value || "—" },
  { title: "投递来源", dataIndex: "apply_source", width: 110, render: (value) => value || "—" },
  { title: "投递日期", dataIndex: "apply_date", width: 120 },
  {
    title: "状态",
    dataIndex: "status",
    width: 120,
    render: (status: string) => <Tag color={status === "offer" ? "green" : "blue"}>{status}</Tag>,
  },
  { title: "备注", dataIndex: "notes", width: 220, render: (value) => value || "—" },
];

const statusOptions = [
  "已投递",
  "待测评",
  "测评已完成",
  "待笔试",
  "笔试已完成",
  "一面待进行",
  "一面通过",
  "二面待进行",
  "二面通过",
  "HR面待进行",
  "offer",
  "未通过",
  "已放弃",
].map((value) => ({ value, label: value }));

export default function ApplicationsPage() {
  const [rows, setRows] = useState<ApplicationRecord[]>([]);
  const [keyword, setKeyword] = useState("");
  const [status, setStatus] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getApplications({ keyword, status })
      .then((result) => {
        if (!cancelled) setRows(result);
      })
      .catch((reason: Error) => {
        if (!cancelled) setError(reason.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [keyword, status, reload]);

  return (
    <>
      <PageHeader title="投递管理" description="浏览并筛选 V1 SQLite 中的真实投递记录。" />
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          allowClear
          placeholder="搜索公司、岗位或地点"
          style={{ width: 280 }}
          onSearch={(value) => setKeyword(value.trim())}
        />
        <Select
          allowClear
          placeholder="筛选状态"
          style={{ width: 180 }}
          options={statusOptions}
          onChange={(value) => setStatus(value)}
        />
      </Space>
      {error ? (
        <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />
      ) : (
        <Spin spinning={loading} tip="正在加载投递记录">
          <Table
            rowKey={(row) => row.id ?? `${row.company}-${row.position}`}
            columns={columns}
            dataSource={rows}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            locale={{ emptyText: <EmptyState description="没有符合条件的投递记录" /> }}
            scroll={{ x: 1220 }}
          />
        </Spin>
      )}
    </>
  );
}
