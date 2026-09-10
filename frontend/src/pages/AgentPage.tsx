import { useEffect, useRef, useState } from "react";
import { Button, Card, Input, Space, Spin, Tag, Typography } from "antd";

import {
  confirmAgentPreview,
  sendAgentMessage,
  type AgentModelUsage,
  type AgentPreview,
  type AgentResponse,
} from "../api/agent";
import { getModelHealth, type ModelHealth } from "../api/model";
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

const AGENT_SESSION_STORAGE_KEY = "jobhunt-ledger.agent-session.v1";
const STATUS_AMBIGUITY_MESSAGE =
  "找到多条匹配记录，当前无法唯一判断你问的是哪一条，请根据投递日期、来源、岗位或当前状态进一步说明；如果这些信息仍然相同，请先处理重复记录。";
const DEFAULT_MODEL_NAME = "qwen2.5-7b-instruct";
const MISSING_FIELD_LABELS: Record<string, string> = {
  company: "公司",
  position: "岗位",
  status: "当前状态",
  apply_date: "投递日期",
  apply_link: "投递链接",
  location: "工作地点",
  apply_source: "投递来源",
  recruit_type: "招聘类型",
  notes: "备注",
  interview_time: "面试时间",
  interview_method: "面试方式",
  stage: "面试阶段",
  meeting_link: "会议链接",
};

interface ConversationMessage {
  id: number;
  role: AgentMessageRole;
  content: string;
  details?: string[];
  model?: AgentModelUsage;
}

interface StoredAgentSession {
  messages: ConversationMessage[];
  pendingPreview: AgentPreview | null;
}

function loadAgentSession(): StoredAgentSession {
  const emptySession: StoredAgentSession = { messages: [], pendingPreview: null };
  try {
    const raw = window.sessionStorage.getItem(AGENT_SESSION_STORAGE_KEY);
    if (!raw) return emptySession;
    const stored = JSON.parse(raw) as Partial<StoredAgentSession>;
    return {
      messages: Array.isArray(stored.messages) ? stored.messages : [],
      pendingPreview:
        stored.pendingPreview && typeof stored.pendingPreview.preview_id === "string"
          ? stored.pendingPreview
          : null,
    };
  } catch {
    return emptySession;
  }
}

function recordsFrom(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

function isAmbiguousStatusQuery(response: AgentResponse): boolean {
  return (
    response.intent === "query_application_status" &&
    (response.data?.status === "ambiguous" || recordsFrom(response.data?.candidates).length > 0)
  );
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
      const fields = Array.isArray(item.missing_fields)
        ? item.missing_fields
            .map((field) => MISSING_FIELD_LABELS[String(field)] || String(field))
            .join("、")
        : "待确认";
      return `${item.company || "未知公司"} · ${item.position || "岗位待补充"}：${fields}`;
    });
  }

  const candidates = recordsFrom(data.candidates);
  if (candidates.length) {
    return candidates.map((item) =>
      [
        item.company || "未知公司",
        item.position || "岗位待补充",
        `投递日期：${item.apply_date || "待补充"}`,
        `来源：${item.apply_source || "待补充"}`,
        `状态：${item.status || "待补充"}`,
      ].join(" · "),
    );
  }

  if (response.intent === "query_application_status") return [];

  const application = data.application;
  if (application && typeof application === "object") {
    const item = application as Record<string, unknown>;
    return [`${item.company || "未知公司"} · ${item.position || "岗位待补充"} · ${item.status || "状态待补充"}`];
  }
  return [];
}

export default function AgentPage() {
  const [initialSession] = useState(loadAgentSession);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>(initialSession.messages);
  const [pendingPreview, setPendingPreview] = useState<AgentPreview | null>(
    initialSession.pendingPreview,
  );
  const [sending, setSending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  const [modelHealthLoading, setModelHealthLoading] = useState(true);
  const [modelHealthError, setModelHealthError] = useState("");
  const nextId = useRef(
    initialSession.messages.reduce((largest, message) => Math.max(largest, message.id), 0) + 1,
  );
  const endRef = useRef<HTMLDivElement | null>(null);

  const appendMessage = (
    role: AgentMessageRole,
    content: string,
    details?: string[],
    model?: AgentModelUsage,
  ) => {
    const message = { id: nextId.current++, role, content, details, model };
    setMessages((current) => [...current, message]);
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, pendingPreview, sending]);

  useEffect(() => {
    let cancelled = false;
    getModelHealth()
      .then((result) => {
        if (!cancelled) setModelHealth(result);
      })
      .catch((reason: Error) => {
        if (!cancelled) setModelHealthError(reason.message);
      })
      .finally(() => {
        if (!cancelled) setModelHealthLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        AGENT_SESSION_STORAGE_KEY,
        JSON.stringify({ messages, pendingPreview }),
      );
    } catch {
      // 浏览器禁用或限制存储时，页面继续以内存会话正常工作。
    }
  }, [messages, pendingPreview]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending || confirming || pendingPreview) return;

    appendMessage("user", text);
    setInput("");
    setSending(true);
    setPreviewError("");
    try {
      const response = await sendAgentMessage(text);
      const ambiguousStatusQuery = isAmbiguousStatusQuery(response);
      appendMessage(
        response.ok || ambiguousStatusQuery ? "assistant" : "error",
        ambiguousStatusQuery ? STATUS_AMBIGUITY_MESSAGE : response.message,
        responseDetails(response),
        response.intent.startsWith("query_") ? response.model : undefined,
      );
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

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size={[12, 8]}>
          <Typography.Text strong>规则 Agent</Typography.Text>
          <Tag color="green">可用</Tag>
          <Typography.Text strong>LM Studio</Typography.Text>
          <Tag
            color={
              modelHealthLoading ? "processing" : modelHealth?.model_available ? "green" : "orange"
            }
          >
            {modelHealthLoading ? "检查中" : modelHealth?.model_available ? "可用" : "不可用"}
          </Tag>
          <Typography.Text>
            当前模型：{modelHealth?.configured_model || DEFAULT_MODEL_NAME}
          </Typography.Text>
        </Space>
        <div style={{ marginTop: 6 }}>
          <Typography.Text type="secondary">
            LM Studio 可用于查询回答润色；即使不可用，基础查询、预览和确认操作仍可正常使用。
          </Typography.Text>
          {!modelHealthLoading && (modelHealthError || modelHealth?.error) ? (
            <Typography.Text type="danger" style={{ marginLeft: 12 }}>
              {modelHealthError
                ? `模型状态检查失败：${modelHealthError}`
                : `LM Studio：${modelHealth?.error}`}
            </Typography.Text>
          ) : null}
        </div>
      </Card>

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
                model={message.model}
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
