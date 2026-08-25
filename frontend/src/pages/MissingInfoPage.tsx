import { useEffect, useState } from "react";
import { Spin, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";

import { getMissingInfo, type MissingInfoRecord } from "../api/missing";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageHeader from "../components/PageHeader";

const columns: ColumnsType<MissingInfoRecord> = [
  { title: "公司", dataIndex: "company", width: 220 },
  { title: "岗位", dataIndex: "position", width: 180 },
  {
    title: "缺失字段",
    dataIndex: "missing_fields",
    render: (fields: string[]) => fields.map((field) => <Tag key={field}>{field}</Tag>),
  },
  { title: "建议补充提示词", dataIndex: "suggestion" },
];

export default function MissingInfoPage() {
  const [rows, setRows] = useState<MissingInfoRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getMissingInfo()
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
  }, [reload]);

  return (
    <>
      <PageHeader title="缺失信息" description="检查投递和面试记录中建议继续补充的字段。" />
      {error ? (
        <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />
      ) : (
        <Spin spinning={loading} tip="正在检查缺失信息">
          <Table
            rowKey={(row) => `${row.company}-${row.position}-${row.missing_fields.join("-")}`}
            columns={columns}
            dataSource={rows}
            pagination={false}
            locale={{ emptyText: <EmptyState description="当前没有明显缺失信息。" /> }}
            scroll={{ x: 800 }}
          />
        </Spin>
      )}
    </>
  );
}
