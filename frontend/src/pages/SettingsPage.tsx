import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Space, Spin, Tag, Typography } from "antd";

import { getModelHealth, type ModelHealth } from "../api/model";
import PageHeader from "../components/PageHeader";

export default function SettingsPage() {
  const [health, setHealth] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getModelHealth()
      .then((result) => {
        if (!cancelled) setHealth(result);
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
      <PageHeader title="系统设置" description="查看本地模型服务状态；本页面不保存或展示敏感配置。" />
      <Card
        title="模型服务"
        extra={
          <Button loading={loading} onClick={() => setReload((value) => value + 1)}>
            刷新状态
          </Button>
        }
      >
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          {error ? (
            <Alert type="warning" showIcon message="模型状态检查失败" description={error} />
          ) : null}
          <Spin spinning={loading} tip="正在检查 LM Studio">
            <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
              <Descriptions.Item label="Provider">{health?.provider || "LM Studio"}</Descriptions.Item>
              <Descriptions.Item label="Base URL">{health?.base_url || "—"}</Descriptions.Item>
              <Descriptions.Item label="配置模型">
                {health?.configured_model || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="已加载模型">
                {health?.loaded_models.length ? (
                  <Space wrap>
                    {health.loaded_models.map((model) => (
                      <Tag key={model}>{model}</Tag>
                    ))}
                  </Space>
                ) : (
                  "未检测到"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="服务是否可连接">
                <Tag color={health?.server_reachable ? "green" : "orange"}>
                  {health?.server_reachable ? "是" : "否"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模型是否可用">
                <Tag color={health?.model_available ? "green" : "orange"}>
                  {health?.model_available ? "是" : "否"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="错误说明" span={2}>
                {error || health?.error || "无"}
              </Descriptions.Item>
            </Descriptions>
          </Spin>

          <Alert
            type="info"
            showIcon
            message="规则 Agent 保证基础功能稳定"
            description="LM Studio 将在后续版本用于回答润色和 unknown 意图辅助。模型不可用时，投递、面试、状态查询、预览和确认仍可继续使用。"
          />
          <Typography.Text type="secondary">
            当前页面仅展示运行状态，不提供模型切换、地址编辑或 API Key 配置。
          </Typography.Text>
        </Space>
      </Card>
    </>
  );
}
