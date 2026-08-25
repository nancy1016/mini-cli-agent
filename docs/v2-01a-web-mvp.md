# JobHuntLedger-Agent V2-01A：Web 主体骨架 MVP

## 阶段目标

V2-01A 在冻结的 V1 求职台账之上建立长期 Web 产品的第一版骨架。后端通过 adapter 只读复用现有 `jobhunt` 模块和 SQLite 数据，前端在浏览器中展示工作台、投递、面试和缺失信息等真实数据。

本阶段不改写 V1 业务逻辑，不迁移数据库，也不实现数据写入。

## 技术选型

- 后端：FastAPI
- 前端：React、TypeScript、Vite、Ant Design、React Router
- 数据：继续使用 V1 SQLite `data/jobhunt.db`
- 业务复用：`backend/app/services/v1_adapter.py` 调用现有 Repository 和 Service
- 测试：pytest、FastAPI TestClient、临时 SQLite

## 后端 API

API 统一前缀为 `/api/v1`：

- `GET /api/v1/health`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/applications?status=&keyword=`
- `GET /api/v1/interviews?range=next_three_days`
- `GET /api/v1/missing-info`

面试范围支持：`today`、`tomorrow`、`next_three_days`、`this_week`、`next_thirty_days`。

## 安装依赖

本阶段没有自动安装任何依赖。请在项目根目录手动执行：

```powershell
python -m pip install -r requirements.txt
```

前端依赖请手动安装：

```powershell
cd frontend
npm install
```

## 启动后端

在项目根目录执行：

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后可访问：

- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`

后端默认读取项目根目录下的 `data/jobhunt.db`。应始终从项目根目录启动后端。

## 启动前端

安装前端依赖后，在 `frontend` 目录执行：

```powershell
npm run dev
```

打开 `http://127.0.0.1:5173`。前端默认请求 `http://127.0.0.1:8000/api/v1`，也可通过 `VITE_API_BASE_URL` 覆盖。

## 已实现页面

- 工作台：统计卡片、最近投递、近期面试
- 投递管理：列表、公司/岗位/地点关键词搜索、状态筛选
- 面试管理：今天、明天、未来 3 天、本周、未来 30 天范围查询
- 缺失信息：投递和面试建议补充字段
- Agent 助手：后续能力占位
- 面经管理：后续能力占位
- 分析中心：后续能力占位
- 系统设置：后续能力占位

## 暂不实现

- 投递、面试的新增、编辑和删除
- PostgreSQL 和数据库迁移
- Docker 和部署
- 登录鉴权
- TXT、DOCX、PDF 面经导入
- Web Agent 真实对话
- Playwright 浏览器测试
- 生产环境配置

## 测试

后端 API 测试使用 pytest 临时目录中的 SQLite，不会读写正式数据库：

```powershell
python -m pytest backend/tests -q
python -m pytest
```

安装前端依赖后可验证生产构建：

```powershell
cd frontend
npm run build
```
