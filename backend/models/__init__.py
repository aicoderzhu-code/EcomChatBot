"""
数据库模型
"""
from models.admin import Admin, AdminOperationLog, PermissionTemplate
from models.audit_log import AuditLog, AuditEventType, AuditSeverity
from models.base import BaseModel, TenantBaseModel
from models.conversation import Conversation, Message, User
from models.knowledge import KnowledgeBase, KnowledgeUsageLog
from models.knowledge_settings import KnowledgeSettings
from models.knowledge_version import KnowledgeVersion
from models.qa_pair import QAPair
from models.payment import (
    OrderStatus,
    PaymentChannel,
    PaymentChannelConfig,
    PaymentOrder,
    PaymentTransaction,
    PaymentType,
    SubscriptionType,
    TransactionStatus,
    TransactionType,
)
from models.invoice import Invoice, InvoiceTitle, InvoiceType, InvoiceStatus
from models.tenant import Bill, Subscription, Tenant
from models.webhook import WebhookConfig, WebhookLog, WebhookEventType
from models.notification import InAppNotification, NotificationPreference
from models.after_sale import AfterSaleRecord
from models.platform import PlatformConfig
from models.platform_app import PlatformApp
from models.webhook_event import WebhookEvent
from models.product import (
    Product, PlatformSyncTask, ProductSyncSchedule,
    ProductStatus, SyncTarget, SyncType, SyncTaskStatus,
)
from models.product_prompt import ProductPrompt, PromptType
from models.generation import (
    GenerationTask, GeneratedAsset,
    GenerationTaskType, GenerationTaskStatus, AssetType,
)
from models.content_template import ContentTemplate, PlatformMediaSpec
from models.pricing import CompetitorProduct, PricingAnalysis, PricingStrategy
from models.order import (
    Order, AnalysisReport,
    OrderStatus as PlatformOrderStatus,
    ReportType, ReportStatus,
)
from models.sensitive_word import SensitiveWord
from models.customer_segment import CustomerSegment, CustomerSegmentMember, SegmentType
from models.outreach import (
    OutreachCampaign, OutreachRule, OutreachTask,
    CampaignType, CampaignStatus, ContentStrategy, OutreachTaskStatus, RuleType,
)
from models.follow_up import FollowUpPlan, FollowUpReason, FollowUpStatus
from models.quota import TenantQuota
from models.knowledge_candidate import KnowledgeCandidate
from models.recommendation import (
    RecommendationRule, RecommendationLog,
    RecommendRuleType, RecommendTriggerType, RecommendStrategy,
)

__all__ = [
    # Base
    "BaseModel",
    "TenantBaseModel",
    # Admin
    "Admin",
    "AdminOperationLog",
    "PermissionTemplate",
    # Audit
    "AuditLog",
    "AuditEventType",
    "AuditSeverity",
    # Tenant
    "Tenant",
    "Subscription",
    "Bill",
    # Conversation
    "User",
    "Conversation",
    "Message",
    # Knowledge
    "KnowledgeBase",
    "KnowledgeUsageLog",
    "KnowledgeSettings",
    "KnowledgeVersion",
    "QAPair",
    "KnowledgeCandidate",
    # Payment
    "PaymentOrder",
    "PaymentTransaction",
    "PaymentChannelConfig",
    "OrderStatus",
    "PaymentChannel",
    "PaymentType",
    "SubscriptionType",
    "TransactionType",
    "TransactionStatus",
    # Webhook
    "WebhookConfig",
    "WebhookLog",
    "WebhookEventType",
    # Notification
    "InAppNotification",
    "NotificationPreference",
    # Platform
    "PlatformConfig",
    "PlatformApp",
    "AfterSaleRecord",
    "WebhookEvent",
    # Product
    "Product",
    "PlatformSyncTask",
    "ProductSyncSchedule",
    "ProductStatus",
    "SyncTarget",
    "SyncType",
    "SyncTaskStatus",
    # Product Prompt
    "ProductPrompt",
    "PromptType",
    # Generation
    "GenerationTask",
    "GeneratedAsset",
    "GenerationTaskType",
    "GenerationTaskStatus",
    "AssetType",
    # Content Template
    "ContentTemplate",
    "PlatformMediaSpec",
    # Pricing
    "CompetitorProduct",
    "PricingAnalysis",
    "PricingStrategy",
    # Order & Report
    "Order",
    "AnalysisReport",
    "PlatformOrderStatus",
    "ReportType",
    "ReportStatus",
    # Sensitive Word
    "SensitiveWord",
    # Customer Segment
    "CustomerSegment",
    "CustomerSegmentMember",
    "SegmentType",
    # Outreach
    "OutreachCampaign",
    "OutreachRule",
    "OutreachTask",
    "CampaignType",
    "CampaignStatus",
    "ContentStrategy",
    "OutreachTaskStatus",
    "RuleType",
    # Follow Up
    "FollowUpPlan",
    "FollowUpReason",
    "FollowUpStatus",
    # Recommendation
    "RecommendationRule",
    "RecommendationLog",
    "RecommendRuleType",
    "RecommendTriggerType",
    "RecommendStrategy",
    # Quota
    "TenantQuota",
]
