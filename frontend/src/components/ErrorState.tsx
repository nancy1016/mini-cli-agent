import { Alert, Button, Space } from "antd";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Alert
      type="error"
      showIcon
      message="数据加载失败"
      description={
        <Space direction="vertical">
          <span>{message}</span>
          {onRetry ? (
            <Button size="small" onClick={onRetry}>
              重新加载
            </Button>
          ) : null}
        </Space>
      }
    />
  );
}
