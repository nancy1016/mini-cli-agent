import { useEffect, useRef, useState } from "react";
import { Button, Card, Input, Space, Spin, Tag, Typography } from "antd";

import {
  confirmAgentPreview,
  sendAgentMessage,
  type AgentPreview,
  type AgentResponse,
} from "../api/agent";
import AgentMessageBubble, {
  type AgentMessageRole,
} from "../components/AgentMessageBubble";
import AgentPreviewCard from "../components/AgentPreviewCard";
import PageHeader from "../components/PageHeader";

const exampleCommands = [
  "我现在投了哪些公司？",
  "这周有哪些面试？",
  "帮我看看哪些信息没填完整？",
  "西安吉利科技公司目前是什么状态？",
  "今天在官网投递了上海百胜软件公司的软件开发岗，地点上海。",
  "明天下午三点，西安吉利科技公司测试开发岗一面，电话通知的。",
  "西安吉利科技公司一面通过了。",
];

interface ConversationMessage {
  id: number;
  role: AgentMessageRole;
  content: string;
  details?: string[];
}

function recordsFrom(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

function responseDetails(response: AgentResponse): string[] {
  const data = response.data;
  if (!data) return [];

  const applications = recordsFrom(data.applications);
  if (applications.length) {
    return applications.slice(0, 8).map(
      (item) => `${item.company || "未知公司"} · ${item.position || "岗位待补充"} · ${item.status || "状态待补充"}`,
    );
  }

  const interviews = recordsFrom(data.interviews);
  if (interviews.length) {
    return interviews.slice(0, 8).map(
      (item) => `${item.interview_time || "时间待补充"} · ${item.company || "未知公司"} · ${item.position || "岗位待补充"} · ${item.stage || "阶段待补充"}`,
    );
  }

  const missingItems = recordsFrom(data.items);
  if (missingItems.length) {
    return missingItems.slice(0, 8).map((item) => {
      const fields = Array.isArray(item.missing_fields) ? item.missing_fields.join("、") : "待确认";
      return `${item.company || "未知公司"} · ${item.position || "岗位待补充"}：${fields}`;
    });
  }

  const candidates = recordsFrom(data.candidates);
  if (candidates.length) {
    return candidates.map(
      (item) => `${item.company || "未知公司"} · ${item.position || "岗位待补充"} · ${item.status || "状态待补充"}`,
    );
  }

  const application = data.application;
  if (application && typeof application === "object") {
    const item = application as Record<string, unknown>;
    return [`${item.company || "未知公司"} · ${item.position || "岗位待补充"} · ${item.status || "状态待补充"}`];
  }
  return [];
}

export default function AgentPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [pendingPreview, setPendingPreview] = useState<AgentPreview | null>(null);
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement | null>(null);

  const appendMessage = (role: AgentMessageRole, content: string, details?: string[]) => {
    const message = { id: nextId.current++, role, content, details };
    setMessages((current) => [...current, message]);
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, pendingPreview, sending]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending || confirming || pendingPreview) return;

    appendMessage("user", text);
    setInput("");
    setSending(true);
    setPreviewError("");
    try {
      const response = await sendAgentMessage(text);
      appendMessage(response.ok ? "assistant" : "error", response.message, responseDetails(response));
      if (response.requires_confirmation && response.preview) {
        setPendingPreview(response.preview);
      }
    } catch (reason) {
      appendMessage("error", reason instanceof Error ? reason.message : "Agent 请求失败，请稍后重试。");
    } finally {
      setSending(false);
    }
  };

  const handleConfirm = async () => {
    if (!pendingPreview || confirming) return;
    setConfirming(true);
    setPreviewError("");
    try {
      const response = await confirmAgentPreview(pendingPreview.preview_id);
      appendMessage(response.ok ? "assistant" : "error", response.message, responseDetails(response));
      if (response.ok) setPendingPreview(null);
    } catch (reason) {
      setPreviewError(reason instanceof Error ? reason.message : "确认失败，请稍后重试。");
    } finally {
      setConfirming(false);
    }
  };

  const handleCancel = () => {
    setPendingPreview(null);
    setPreviewError("");
    appendMessage("assistant", "已取消，本次未写入数据库。");
  };

  return (
    <>
      <PageHeader
        title="Agent 助手"
        description="用自然语言管理求职记录和面试提醒。查询操作会直接返回结果，新增和更新操作会先展示预览，确认后才保存。"
      />

      <Card size="small" title="试试这些指令" style={{ marginBottom: 16 }}>
        <Space wrap>
          {exampleCommands.map((command) => (
            <Tag
              color="blue"
              key={command}
              style={{ cursor: pendingPreview ? "not-allowed" : "pointer", padding: "5px 9px" }}
              onClick={() => {
                if (!pendingPreview) setInput(command);
              }}
            >
              {command}
            </Tag>
          ))}
        </Space>
      </Card>

      <Card
        title="对话"
        styles={{ body: { padding: 16 } }}
        style={{ marginBottom: 16 }}
      >
        <div
          aria-live="polite"
          style={{
            minHeight: 300,
            maxHeight: "52vh",
            overflowY: "auto",
            padding: 4,
          }}
        >
          <Space direction="vertical" size={14} style={{ width: "100%" }}>
            {messages.length === 0 ? (
              <Typography.Text type="secondary">
                输入一条求职指令开始对话。查询会立即返回，写入操作需要你再次确认。
              </Typography.Text>
            ) : null}
            {messages.map((message) => (
              <AgentMessageBubble
                key={message.id}
                role={message.role}
                content={message.content}
                details={message.details}
              />
            ))}
            {pendingPreview ? (
              <AgentPreviewCard
                preview={pendingPreview}
                confirming={confirming}
                error={previewError}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
              />
            ) : null}
            {sending ? (
              <Space>
                <Spin size="small" />
                <Typography.Text type="secondary">Agent 正在处理...</Typography.Text>
              </Space>
            ) : null}
            <div ref={endRef} />
          </Space>
        </div>
      </Card>

      <Space.Compact style={{ width: "100%" }}>
        <Input.TextArea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              void handleSend();
            }
          }}
          autoSize={{ minRows: 3, maxRows: 6 }}
          disabled={sending || confirming || Boolean(pendingPreview)}
          placeholder={
            pendingPreview
              ? "请先确认或取消当前预览"
              : "输入求职指令，Enter 发送，Shift+Enter 换行"
          }
        />
        <Button
          type="primary"
          size="large"
          loading={sending}
          disabled={!input.trim() || confirming || Boolean(pendingPreview)}
          onClick={() => void handleSend()}
          style={{ height: "auto", minWidth: 96 }}
        >
          发送
        </Button>
      </Space.Compact>
    </>
  );
}
