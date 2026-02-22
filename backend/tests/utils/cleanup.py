"""
测试数据清理工具
"""
from typing import List
from rich.console import Console

console = Console()


class TestDataCleaner:
    """测试数据清理器"""

    def __init__(self):
        self.tenant_ids: List[str] = []
        self.conversation_ids: List[str] = []
        self.knowledge_ids: List[str] = []
        self.model_config_ids: List[str] = []
        self.webhook_ids: List[int] = []
        self.sensitive_word_ids: List[int] = []
        self.payment_order_numbers: List[str] = []

    def register_tenant(self, tenant_id: str):
        """注册需要清理的租户"""
        if tenant_id not in self.tenant_ids:
            self.tenant_ids.append(tenant_id)
            console.print(f"[yellow]📝 注册清理: 租户 {tenant_id}[/yellow]")

    def register_conversation(self, conversation_id: str):
        """注册需要清理的对话"""
        if conversation_id not in self.conversation_ids:
            self.conversation_ids.append(conversation_id)
            console.print(f"[yellow]📝 注册清理: 对话 {conversation_id}[/yellow]")

    def register_knowledge(self, knowledge_id: str):
        """注册需要清理的知识条目"""
        if knowledge_id not in self.knowledge_ids:
            self.knowledge_ids.append(knowledge_id)
            console.print(f"[yellow]📝 注册清理: 知识 {knowledge_id}[/yellow]")

    def register_model_config(self, config_id: str):
        """注册需要清理的模型配置"""
        if config_id not in self.model_config_ids:
            self.model_config_ids.append(config_id)
            console.print(f"[yellow]📝 注册清理: 模型配置 {config_id}[/yellow]")

    def register_webhook(self, webhook_id: int):
        """注册需要清理的 Webhook"""
        if webhook_id not in self.webhook_ids:
            self.webhook_ids.append(webhook_id)
            console.print(f"[yellow]📝 注册清理: Webhook {webhook_id}[/yellow]")

    def register_sensitive_word(self, word_id: int):
        """注册需要清理的敏感词"""
        if word_id not in self.sensitive_word_ids:
            self.sensitive_word_ids.append(word_id)
            console.print(f"[yellow]📝 注册清理: 敏感词 {word_id}[/yellow]")

    def register_payment_order(self, order_number: str):
        """注册需要清理的支付订单"""
        if order_number not in self.payment_order_numbers:
            self.payment_order_numbers.append(order_number)
            console.print(f"[yellow]📝 注册清理: 支付订单 {order_number}[/yellow]")

    async def cleanup_all(self, client):
        """清理所有注册的测试数据"""
        console.print("\n[cyan]🧹 开始清理测试数据...[/cyan]")

        # 清理敏感词（需要管理员权限，可能需要先登录）
        for word_id in self.sensitive_word_ids:
            try:
                await client.delete(f"/sensitive-words/{word_id}")
                console.print(f"[green]✓ 已删除敏感词: {word_id}[/green]")
            except Exception as e:
                console.print(f"[red]✗ 删除敏感词失败: {str(e)}[/red]")

        # 清理 Webhook
        for webhook_id in self.webhook_ids:
            try:
                await client.delete(f"/webhooks/{webhook_id}")
                console.print(f"[green]✓ 已删除Webhook: {webhook_id}[/green]")
            except Exception as e:
                console.print(f"[red]✗ 删除Webhook失败: {str(e)}[/red]")

        # 清理模型配置
        for config_id in self.model_config_ids:
            try:
                await client.delete(f"/models/{config_id}")
                console.print(f"[green]✓ 已删除模型配置: {config_id}[/green]")
            except Exception as e:
                console.print(f"[red]✗ 删除模型配置失败: {str(e)}[/red]")

        # 清理知识条目
        for knowledge_id in self.knowledge_ids:
            try:
                await client.delete(f"/knowledge/{knowledge_id}")
                console.print(f"[green]✓ 已删除知识: {knowledge_id}[/green]")
            except Exception as e:
                console.print(f"[red]✗ 删除知识失败: {str(e)}[/red]")

        # 清理对话
        for conversation_id in self.conversation_ids:
            try:
                await client.put(
                    f"/conversation/{conversation_id}",
                    json={"status": "closed"}
                )
                console.print(f"[green]✓ 已关闭对话: {conversation_id}[/green]")
            except Exception as e:
                console.print(f"[red]✗ 关闭对话失败: {str(e)}[/red]")

        # 通过管理员接口禁用测试租户
        for tenant_id in self.tenant_ids:
            try:
                await client.put(
                    f"/admin/tenants/{tenant_id}/status",
                    json={"status": "disabled"}
                )
                console.print(f"[green]✓ 已禁用租户: {tenant_id}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ 禁用租户失败(可能无管理员权限): {str(e)}[/yellow]")

        console.print("[cyan]✓ 清理完成[/cyan]\n")

    def clear_registry(self):
        """清空注册列表"""
        self.tenant_ids.clear()
        self.conversation_ids.clear()
        self.knowledge_ids.clear()
        self.model_config_ids.clear()
        self.webhook_ids.clear()
        self.sensitive_word_ids.clear()
        self.payment_order_numbers.clear()

    def get_summary(self) -> dict:
        """获取清理摘要"""
        return {
            "tenants": len(self.tenant_ids),
            "conversations": len(self.conversation_ids),
            "knowledge": len(self.knowledge_ids),
            "model_configs": len(self.model_config_ids),
            "webhooks": len(self.webhook_ids),
            "sensitive_words": len(self.sensitive_word_ids),
            "payment_orders": len(self.payment_order_numbers),
        }


# 全局清理器实例
cleaner = TestDataCleaner()
