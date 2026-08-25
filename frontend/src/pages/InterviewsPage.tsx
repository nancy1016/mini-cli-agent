import { useEffect, useState } from "react";
import { Select, Spin, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import {
  getInterviews,
  type InterviewRange,
  type InterviewRecord,
} from "../api/interviews";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";

const columns: ColumnsType<InterviewRecord> = [
  { title: "公司", dataIndex: "company", width: 180 },
  { title: "岗位", dataIndex: "position", width: 150 },
  { title: "时间", dataIndex: "interview_time", width: 170 },
  { title: "阶段", dataIndex: "stage", width: 110 },
  { title: "方式", dataIndex: "interview_method", width: 120, render: (value) => value || "—" },
  {
    title: "会议链接",
    dataIndex: "meeting_link",
    width: 220,
    render: (value: string | null) =>
      value ? (
        <Typography.Link href={value} target="_blank" rel="noreferrer">
          打开会议
        </Typography.Link>
      ) : (
        "—"
      ),
  },
  { title: "备注", dataIndex: "notes", width: 220, render: (value) => value || "—" },
];

const rangeOptions: { value: InterviewRange; label: string }[] = [
  { value: "today", label: "今天" },
  { value: "tomorrow", label: "明天" },
  { value: "next_three_days", label: "未来 3 天" },
  { value: "this_week", label: "本周" },
  { value: "next_thirty_days", label: "未来 30 天" },
];

export default function InterviewsPage() {
  const [range, setRange] = useState<InterviewRange>("next_three_days");
  const [rows, setRows] = useState<InterviewRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getInterviews(range)
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
  }, [range, reload]);

  return (
    <>
      <PageHeader title="面试管理" description="按时间范围查看即将进行的面试安排。" />
      <Select
        value={range}
        options={rangeOptions}
        onChange={(value) => setRange(value)}
        style={{ width: 180, marginBottom: 16 }}
      />
      {error ? (
        <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />
      ) : (
        <Spin spinning={loading} tip="正在加载面试记录">
          <Table
            rowKey={(row) => row.id ?? `${row.company}-${row.interview_time}`}
            columns={columns}
            dataSource={rows}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            locale={{ emptyText: <EmptyState description="当前时间范围内没有面试" /> }}
            scroll={{ x: 1170 }}
          />
        </Spin>
      )}
    </>
  );
}
