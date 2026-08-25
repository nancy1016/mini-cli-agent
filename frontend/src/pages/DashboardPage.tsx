import { useEffect, useState } from "react";
import { Card, Col, Row, Space, Spin, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import { getDashboardSummary, type DashboardSummary } from "../api/dashboard";
import type { ApplicationRecord } from "../api/applications";
import type { InterviewRecord } from "../api/interviews";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";

const applicationColumns: ColumnsType<ApplicationRecord> = [
  { title: "公司", dataIndex: "company" },
  { title: "岗位", dataIndex: "position" },
  { title: "投递日期", dataIndex: "apply_date" },
  {
    title: "状态",
    dataIndex: "status",
    render: (status: string) => <Tag color={status === "offer" ? "green" : "blue"}>{status}</Tag>,
  },
];

const interviewColumns: ColumnsType<InterviewRecord> = [
  { title: "公司", dataIndex: "company" },
  { title: "岗位", dataIndex: "position" },
  { title: "时间", dataIndex: "interview_time" },
  { title: "阶段", dataIndex: "stage" },
];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getDashboardSummary()
      .then((result) => {
        if (!cancelled) setData(result);
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
  }, [reload]);

  if (loading) return <Spin tip="正在加载工作台数据" />;
  if (error) return <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />;
  if (!data) return <EmptyState description="暂无工作台数据" />;

  const statistics = [
    ["投递总数", data.total_applications],
    ["进行中记录", data.active_applications],
    ["Offer 数量", data.offer_count],
    ["未来 3 天面试", data.next_three_days_interviews],
    ["未来 30 天面试", data.next_thirty_days_interviews],
    ["缺失信息记录", data.missing_info_count],
  ] as const;

  return (
    <>
      <PageHeader title="工作台" description="集中查看当前求职进度、近期面试与待补充信息。" />
      <Row gutter={[16, 16]}>
        {statistics.map(([title, value]) => (
          <Col xs={24} sm={12} xl={8} key={title}>
            <Card>
              <Statistic title={title} value={value} />
            </Card>
          </Col>
        ))}
      </Row>

      <Space direction="vertical" size={24} style={{ width: "100%", marginTop: 24 }}>
        <section>
          <Typography.Title level={4}>最近投递</Typography.Title>
          <Table
            rowKey={(row) => row.id ?? `${row.company}-${row.position}`}
            columns={applicationColumns}
            dataSource={data.recent_applications}
            pagination={false}
            locale={{ emptyText: <EmptyState description="还没有投递记录" /> }}
            scroll={{ x: 640 }}
          />
        </section>
        <section>
          <Typography.Title level={4}>近期面试提醒</Typography.Title>
          <Table
            rowKey={(row) => row.id ?? `${row.company}-${row.interview_time}`}
            columns={interviewColumns}
            dataSource={data.upcoming_interviews}
            pagination={false}
            locale={{ emptyText: <EmptyState description="未来 30 天暂无面试" /> }}
            scroll={{ x: 640 }}
          />
        </section>
      </Space>
    </>
  );
}
