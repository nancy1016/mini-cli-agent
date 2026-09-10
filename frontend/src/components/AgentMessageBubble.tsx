import { Alert, Card, List, Space, Tag, Typography } from "antd";

import type { AgentModelUsage } from "../api/agent";

export type AgentMessageRole = "user" | "assistant" | "error";

interface AgentMessageBubbleProps {
  role: AgentMessageRole;
  content: string;
  details?: string[];
  model?: AgentModelUsage;
}

export default function AgentMessageBubble({
  role,
  content,
  details = [],
  model,
}: AgentMessageBubbleProps) {
  if (role === "error") {
    return <Alert type="error" showIcon message="操作失败" description={content} />;
  }

  const isUser = role === "user";
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <Card
        size="small"
        styles={{ body: { padding: "12px 16px" } }}
        style={{
          maxWidth: "82%",
          background: isUser ? "#1677ff" : "#f5f7fa",
          borderColor: isUser ? "#1677ff" : "#e5e7eb",
        }}
      >
        <Typography.Text style={{ color: isUser ? "white" : undefined, whiteSpace: "pre-wrap" }}>
          {content}
        </Typography.Text>
        {details.length ? (
          <List
            size="small"
            dataSource={details}
            style={{ marginTop: 8 }}
            renderItem={(item) => (
              <List.Item style={{ padding: "4px 0", color: isUser ? "white" : undefined }}>
                {item}
              </List.Item>
            )}
          />
        ) : null}
        {!isUser && model ? (
          <Space size={6} style={{ marginTop: 8 }}>
            {model.used ? (
              <Tag color="purple">LM Studio 已润色</Tag>
            ) : model.fallback_reason ? (
              <Tag color="orange">模型不可用，已使用规则回答</Tag>
            ) : (
              <Tag>规则 Agent 回答</Tag>
            )}
          </Space>
        ) : null}
      </Card>
    </div>
  );
}
