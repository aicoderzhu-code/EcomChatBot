"""
WebSocket 连接管理服务
"""
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        """初始化连接管理器"""
        # 存储活跃连接: {tenant_id: {conversation_id: websocket}}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        conversation_id: str,
    ) -> None:
        """
        接受新的 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接
            tenant_id: 租户 ID
            conversation_id: 会话 ID
        """
        await websocket.accept()

        # 添加连接
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = {}

        self.active_connections[tenant_id][conversation_id] = websocket

        # 发送欢迎消息
        await self.send_system_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            message="连接成功，开始对话",
        )

    def disconnect(self, tenant_id: str, conversation_id: str) -> None:
        """
        断开连接
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
        """
        if tenant_id in self.active_connections:
            if conversation_id in self.active_connections[tenant_id]:
                del self.active_connections[tenant_id][conversation_id]

            # 如果租户没有连接了，删除租户键
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]

    async def send_message(
        self,
        tenant_id: str,
        conversation_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        发送消息到特定连接
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            message: 消息内容（字典）
        """
        if tenant_id in self.active_connections:
            if conversation_id in self.active_connections[tenant_id]:
                websocket = self.active_connections[tenant_id][conversation_id]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"发送消息失败: {e}")
                    self.disconnect(tenant_id, conversation_id)

    async def send_text_message(
        self,
        tenant_id: str,
        conversation_id: str,
        content: str,
        role: str = "assistant",
    ) -> None:
        """
        发送文本消息
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            content: 消息内容
            role: 角色（user/assistant/system）
        """
        message = {
            "type": "message",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_message(tenant_id, conversation_id, message)

    async def send_system_message(
        self,
        tenant_id: str,
        conversation_id: str,
        message: str,
    ) -> None:
        """
        发送系统消息
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            message: 系统消息内容
        """
        data = {
            "type": "system",
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_message(tenant_id, conversation_id, data)

    async def send_streaming_chunk(
        self,
        tenant_id: str,
        conversation_id: str,
        chunk: str,
        is_final: bool = False,
    ) -> None:
        """
        发送流式输出的块
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            chunk: 文本块
            is_final: 是否是最后一块
        """
        message = {
            "type": "stream",
            "chunk": chunk,
            "is_final": is_final,
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_message(tenant_id, conversation_id, message)

    async def send_error(
        self,
        tenant_id: str,
        conversation_id: str,
        error_message: str,
        error_code: str = "ERROR",
    ) -> None:
        """
        发送错误消息
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            error_message: 错误消息
            error_code: 错误代码
        """
        message = {
            "type": "error",
            "error": {
                "code": error_code,
                "message": error_message,
            },
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_message(tenant_id, conversation_id, message)

    async def broadcast_to_tenant(self, tenant_id: str, message: dict[str, Any]) -> None:
        """
        广播消息到租户的所有连接
        
        Args:
            tenant_id: 租户 ID
            message: 消息内容
        """
        if tenant_id in self.active_connections:
            for conversation_id in list(
                self.active_connections[tenant_id].keys()
            ):  # 复制键列表
                await self.send_message(tenant_id, conversation_id, message)

    def get_connection_count(self, tenant_id: str | None = None) -> int:
        """
        获取连接数量
        
        Args:
            tenant_id: 租户 ID（可选），如果不提供则返回总连接数
            
        Returns:
            连接数量
        """
        if tenant_id:
            return (
                len(self.active_connections.get(tenant_id, {}))
                if tenant_id in self.active_connections
                else 0
            )
        else:
            return sum(len(conns) for conns in self.active_connections.values())

    def is_connected(self, tenant_id: str, conversation_id: str) -> bool:
        """
        检查连接是否存在
        
        Args:
            tenant_id: 租户 ID
            conversation_id: 会话 ID
            
        Returns:
            是否连接
        """
        return (
            tenant_id in self.active_connections
            and conversation_id in self.active_connections[tenant_id]
        )

    def get_stats(self) -> dict[str, Any]:
        """
        获取连接统计
        
        Returns:
            统计信息
        """
        return {
            "total_connections": self.get_connection_count(),
            "tenants_online": len(self.active_connections),
            "connections_by_tenant": {
                tid: len(conns) for tid, conns in self.active_connections.items()
            },
        }


# 全局连接管理器实例
connection_manager = ConnectionManager()
