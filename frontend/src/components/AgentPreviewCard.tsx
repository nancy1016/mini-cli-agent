import { Alert, Button, Card, Descriptions, Space, Tag, Typography } from "antd";

import type { AgentMissingFields, AgentPreview, AgentPreviewType } from "../api/agent";

interface AgentPreviewCardProps {
  preview: AgentPreview;
  confirming: boolean;
  error?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const fieldDefinitions: Record<AgentPreviewType, Array<[string, string]>> = {
  application: [
    ["company", "公司"],
    ["position", "岗位"],
    ["location", "地点"],
    ["recruit_type", "招聘类型"],
    ["apply_source", "投递渠道"],
    ["apply_link", "投递链接"],
    ["apply_date", "投递日期"],
    ["status", "当前状态"],
    ["notes", "备注"],
  ],
  interview: [
    ["company", "公司"],
    ["position", "岗位"],
    ["stage", "面试阶段"],
    ["interview_time", "面试时间"],
    ["interview_method", "面试方式"],
    ["matched_application", "关联投递"],
  ],
  status_update: [
    ["company", "公司"],
    ["position", "岗位"],
    ["old_status", "原状态"],
    ["new_status", "新状态"],
  ],
};

const titles: Record<AgentPreviewType, string> = {
  application: "投递记录预览",
  interview: "面试记录预览",
  status_update: "状态更新预览",
};

const fieldLabels: Record<string, string> = {
  company: "公司",
  position: "岗位",
  location: "地点",
  recruit_type: "招聘类型",
  apply_source: "投递渠道",
  apply_link: "投递链接",
  notes: "备注",
  interview_time: "面试时间",
  meeting_link: "会议链接",
};

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "待补充";
  if (typeof value === "object") {
    const item = value as Record<string, unknown>;
    return [item.company, item.position, item.status].filter(Boolean).join(" · ") || "—";
  }
  return String(value);
}

function MissingFields({ missing }: { missing: AgentMissingFields | null }) {
  if (!missing || (!missing.required.length && !missing.recommended.length)) return null;
  return (
    <Space direction="vertical" size={6} style={{ width: "100%" }}>
      <Typography.Text strong>缺失字段</Typography.Text>
      <Space wrap>
        {missing.required.map((field) => (
          <Tag color="red" key={`required-${field}`}>
            必填：{fieldLabels[field] || field}
          </Tag>
        ))}
        {missing.recommended.map((field) => (
          <Tag color="gold" key={`recommended-${field}`}>
            建议：{fieldLabels[field] || field}
          </Tag>
        ))}
      </Space>
    </Space>
  );
}

export default function AgentPreviewCard({
  preview,
  confirming,
  error,
  onConfirm,
  onCancel,
}: AgentPreviewCardProps) {
  return (
    <Card
      title={titles[preview.type]}
      style={{ borderColor: "#91caff", background: "#f0f7ff" }}
    >
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
          {fieldDefinitions[preview.type].map(([key, label]) => (
            <Descriptions.Item label={label} key={key}>
              {displayValue(preview.fields[key])}
            </Descriptions.Item>
          ))}
        </Descriptions>

        <MissingFields missing={preview.missing} />

        {preview.warnings.map((warning) => (
          <Alert key={warning} type="warning" showIcon message={warning} />
        ))}
        {error ? <Alert type="error" showIcon message="确认失败" description={error} /> : null}

        <Space>
          <Button type="primary" loading={confirming} onClick={onConfirm}>
            {preview.type === "status_update" ? "确认更新" : "确认保存"}
          </Button>
          <Button disabled={confirming} onClick={onCancel}>
            取消
          </Button>
        </Space>
      </Space>
    </Card>
  );
}
