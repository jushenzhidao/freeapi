"""路由层。每个文件一个服务（chat/images/videos/audio）。

路由层职责：
- 接收请求并校验
- 调用 registry.lookup() 找到对应厂商
- 调用厂商 handler
- 包装响应（流式/非流式）

不应该包含：
- 任何厂商特定逻辑
- 计费（由 new-api 负责）
- 复杂的业务逻辑
"""
