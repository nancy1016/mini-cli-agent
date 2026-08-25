import { Layout, Menu, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const { Header, Content, Sider } = Layout;

const menuItems = [
  { key: "/dashboard", label: "工作台" },
  { key: "/applications", label: "投递管理" },
  { key: "/interviews", label: "面试管理" },
  { key: "/missing-info", label: "缺失信息" },
  { key: "/agent", label: "Agent 助手" },
  { key: "/experiences", label: "面经管理" },
  { key: "/analysis", label: "分析中心" },
  { key: "/settings", label: "系统设置" },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const selectedKey = location.pathname === "/" ? "/dashboard" : location.pathname;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={220} breakpoint="lg" collapsedWidth={72}>
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "white",
            fontWeight: 700,
            letterSpacing: 0.4,
          }}
        >
          JobHuntLedger
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "white",
            padding: "0 28px",
            borderBottom: "1px solid #f0f0f0",
            display: "flex",
            alignItems: "center",
          }}
        >
          <Typography.Text strong>JobHuntLedger-Agent 求职管理系统</Typography.Text>
        </Header>
        <Content style={{ margin: 24, minWidth: 0 }}>
          <div
            style={{
              background: "white",
              borderRadius: 12,
              padding: 24,
              minHeight: "calc(100vh - 112px)",
            }}
          >
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
