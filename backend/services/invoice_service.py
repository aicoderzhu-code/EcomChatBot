"""
发票服务

包括：
- 发票创建
- PDF发票生成
- 发票发送
- 发票抬头管理
"""
import io
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from models.invoice import Invoice, InvoiceTitle, InvoiceType, InvoiceStatus
from models.tenant import Bill, Tenant


logger = logging.getLogger(__name__)


class InvoiceService:
    """发票服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        # 销售方信息（从配置读取）
        self.seller_name = getattr(settings, "INVOICE_SELLER_NAME", "智能客服科技有限公司")
        self.seller_tax_number = getattr(settings, "INVOICE_SELLER_TAX_NUMBER", "91110000000000000X")
        # 发票存储路径
        self.invoice_storage_path = Path(getattr(settings, "INVOICE_STORAGE_PATH", "./storage/invoices"))
        self.invoice_storage_path.mkdir(parents=True, exist_ok=True)

    async def create_invoice(
        self,
        tenant_id: str,
        bill_id: Optional[int] = None,
        amount: Decimal = Decimal("0"),
        invoice_type: InvoiceType = InvoiceType.ELECTRONIC,
        buyer_name: str = "",
        buyer_tax_number: Optional[str] = None,
        buyer_address: Optional[str] = None,
        buyer_bank_account: Optional[str] = None,
        item_name: str = "信息技术服务费",
        remark: Optional[str] = None,
        recipient_email: Optional[str] = None,
    ) -> Invoice:
        """
        创建发票

        Args:
            tenant_id: 租户ID
            bill_id: 关联账单ID（可选）
            amount: 发票金额
            invoice_type: 发票类型
            buyer_name: 购买方名称
            buyer_tax_number: 购买方税号
            buyer_address: 购买方地址电话
            buyer_bank_account: 购买方开户行及账号
            item_name: 项目名称
            remark: 备注
            recipient_email: 接收邮箱

        Returns:
            创建的发票对象
        """
        # 生成发票号码
        invoice_number = self._generate_invoice_number()

        # 计算税额（默认6%税率）
        tax_rate = Decimal("0.06")
        # 不含税金额 = 含税金额 / (1 + 税率)
        amount_without_tax = amount / (1 + tax_rate)
        tax_amount = amount - amount_without_tax

        # 创建发票记录
        invoice = Invoice(
            invoice_number=invoice_number,
            tenant_id=tenant_id,
            bill_id=bill_id,
            invoice_type=invoice_type,
            status=InvoiceStatus.PENDING,
            amount=amount,
            tax_amount=tax_amount.quantize(Decimal("0.01")),
            tax_rate=tax_rate,
            buyer_name=buyer_name,
            buyer_tax_number=buyer_tax_number,
            buyer_address=buyer_address,
            buyer_bank_account=buyer_bank_account,
            seller_name=self.seller_name,
            seller_tax_number=self.seller_tax_number,
            item_name=item_name,
            item_unit_price=amount_without_tax.quantize(Decimal("0.01")),
            remark=remark,
            recipient_email=recipient_email,
        )

        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)

        logger.info(f"创建发票成功: invoice_number={invoice_number}, tenant={tenant_id}, amount={amount}")

        return invoice

    async def create_invoice_from_bill(
        self,
        bill_id: int,
        title_id: Optional[int] = None,
        recipient_email: Optional[str] = None,
    ) -> Invoice:
        """
        根据账单创建发票

        Args:
            bill_id: 账单ID
            title_id: 发票抬头ID（可选，使用已保存的抬头）
            recipient_email: 接收邮箱

        Returns:
            创建的发票对象
        """
        # 获取账单信息
        stmt = select(Bill).where(Bill.id == bill_id)
        result = await self.db.execute(stmt)
        bill = result.scalar_one_or_none()

        if not bill:
            raise ValueError(f"账单不存在: {bill_id}")

        # 获取购买方信息
        buyer_name = ""
        buyer_tax_number = None
        buyer_address = None
        buyer_bank_account = None
        invoice_type = InvoiceType.ELECTRONIC

        if title_id:
            # 使用保存的发票抬头
            title_stmt = select(InvoiceTitle).where(InvoiceTitle.id == title_id)
            title_result = await self.db.execute(title_stmt)
            title = title_result.scalar_one_or_none()

            if title:
                buyer_name = title.title_name
                buyer_tax_number = title.tax_number
                buyer_address = title.address
                buyer_bank_account = title.bank_account
                invoice_type = title.invoice_type
        else:
            # 使用租户信息作为默认抬头
            tenant_stmt = select(Tenant).where(Tenant.tenant_id == bill.tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()

            if tenant:
                buyer_name = tenant.company_name
                if not recipient_email:
                    recipient_email = tenant.contact_email

        # 创建发票
        return await self.create_invoice(
            tenant_id=bill.tenant_id,
            bill_id=bill_id,
            amount=bill.total_amount,
            invoice_type=invoice_type,
            buyer_name=buyer_name,
            buyer_tax_number=buyer_tax_number,
            buyer_address=buyer_address,
            buyer_bank_account=buyer_bank_account,
            item_name="信息技术服务费",
            remark=f"账单周期: {bill.billing_period}",
            recipient_email=recipient_email,
        )

    async def generate_pdf(self, invoice_id: int) -> str:
        """
        生成发票PDF

        Args:
            invoice_id: 发票ID

        Returns:
            PDF文件路径
        """
        # 获取发票信息
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        # 生成PDF文件
        pdf_filename = f"{invoice.invoice_number}.pdf"
        pdf_path = self.invoice_storage_path / pdf_filename

        # 使用reportlab生成PDF
        pdf_content = self._create_invoice_pdf(invoice)

        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

        # 更新发票记录
        invoice.pdf_path = str(pdf_path)
        await self.db.commit()

        logger.info(f"生成发票PDF成功: invoice={invoice.invoice_number}, path={pdf_path}")

        return str(pdf_path)

    def _create_invoice_pdf(self, invoice: Invoice) -> bytes:
        """
        创建发票PDF内容

        Args:
            invoice: 发票对象

        Returns:
            PDF内容字节
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            logger.warning("reportlab未安装，使用简化PDF生成")
            return self._create_simple_invoice_pdf(invoice)

        buffer = io.BytesIO()

        # 创建PDF文档
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        # 尝试注册中文字体
        try:
            # 尝试常见的中文字体路径
            font_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Ubuntu
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # 通用
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "C:/Windows/Fonts/simhei.ttf",  # Windows
            ]
            font_registered = False
            for font_path in font_paths:
                if Path(font_path).exists():
                    pdfmetrics.registerFont(TTFont("Chinese", font_path))
                    font_registered = True
                    break

            if not font_registered:
                # 如果没有找到中文字体，使用默认字体
                logger.warning("未找到中文字体，PDF将使用默认字体")
        except Exception as e:
            logger.warning(f"注册中文字体失败: {e}")

        # 获取样式
        styles = getSampleStyleSheet()
        try:
            title_style = ParagraphStyle(
                "Title",
                parent=styles["Title"],
                fontName="Chinese",
                fontSize=18,
            )
            normal_style = ParagraphStyle(
                "Normal",
                parent=styles["Normal"],
                fontName="Chinese",
                fontSize=10,
            )
        except Exception:
            title_style = styles["Title"]
            normal_style = styles["Normal"]

        elements = []

        # 标题
        invoice_type_text = {
            InvoiceType.NORMAL: "普通发票",
            InvoiceType.VAT_SPECIAL: "增值税专用发票",
            InvoiceType.ELECTRONIC: "电子发票",
        }.get(invoice.invoice_type, "发票")

        elements.append(Paragraph(invoice_type_text, title_style))
        elements.append(Spacer(1, 10 * mm))

        # 发票基本信息表格
        basic_info = [
            ["发票号码:", invoice.invoice_number, "开票日期:", invoice.issued_at.strftime("%Y-%m-%d") if invoice.issued_at else "-"],
        ]
        basic_table = Table(basic_info, colWidths=[30 * mm, 50 * mm, 30 * mm, 50 * mm])
        basic_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ]))
        elements.append(basic_table)
        elements.append(Spacer(1, 5 * mm))

        # 购买方信息
        buyer_info = [
            ["购买方名称:", invoice.buyer_name],
            ["纳税人识别号:", invoice.buyer_tax_number or "-"],
            ["地址、电话:", invoice.buyer_address or "-"],
            ["开户行及账号:", invoice.buyer_bank_account or "-"],
        ]
        buyer_table = Table(buyer_info, colWidths=[40 * mm, 120 * mm])
        buyer_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        elements.append(buyer_table)
        elements.append(Spacer(1, 5 * mm))

        # 项目明细
        item_data = [
            ["项目名称", "规格型号", "单位", "数量", "单价", "金额"],
            [
                invoice.item_name,
                invoice.item_specification or "-",
                invoice.item_unit,
                str(invoice.item_quantity),
                f"{invoice.item_unit_price:.2f}",
                f"{invoice.amount - invoice.tax_amount:.2f}",
            ],
        ]
        item_table = Table(item_data, colWidths=[50 * mm, 30 * mm, 20 * mm, 20 * mm, 25 * mm, 25 * mm])
        item_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(item_table)
        elements.append(Spacer(1, 5 * mm))

        # 合计
        total_info = [
            ["税率:", f"{invoice.tax_rate * 100:.0f}%", "税额:", f"{invoice.tax_amount:.2f}"],
            ["价税合计(大写):", self._amount_to_chinese(float(invoice.amount)), "(小写):", f"¥{invoice.amount:.2f}"],
        ]
        total_table = Table(total_info, colWidths=[30 * mm, 50 * mm, 30 * mm, 50 * mm])
        total_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ]))
        elements.append(total_table)
        elements.append(Spacer(1, 5 * mm))

        # 销售方信息
        seller_info = [
            ["销售方名称:", invoice.seller_name],
            ["纳税人识别号:", invoice.seller_tax_number],
        ]
        seller_table = Table(seller_info, colWidths=[40 * mm, 120 * mm])
        seller_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        elements.append(seller_table)
        elements.append(Spacer(1, 5 * mm))

        # 备注
        if invoice.remark:
            elements.append(Paragraph(f"备注: {invoice.remark}", normal_style))

        # 构建PDF
        doc.build(elements)

        return buffer.getvalue()

    def _create_simple_invoice_pdf(self, invoice: Invoice) -> bytes:
        """
        创建简化版发票PDF（不依赖reportlab）

        使用纯文本格式生成简化的发票信息

        Args:
            invoice: 发票对象

        Returns:
            PDF内容字节（实际是文本格式）
        """
        # 如果reportlab不可用，生成一个简单的文本格式
        content = f"""
========================================
              电子发票
========================================

发票号码: {invoice.invoice_number}
开票日期: {invoice.issued_at.strftime("%Y-%m-%d") if invoice.issued_at else "-"}

----------------------------------------
购买方信息
----------------------------------------
名称: {invoice.buyer_name}
纳税人识别号: {invoice.buyer_tax_number or "-"}
地址电话: {invoice.buyer_address or "-"}
开户行及账号: {invoice.buyer_bank_account or "-"}

----------------------------------------
项目明细
----------------------------------------
项目名称: {invoice.item_name}
单位: {invoice.item_unit}
数量: {invoice.item_quantity}
单价: ¥{invoice.item_unit_price:.2f}
金额: ¥{invoice.amount - invoice.tax_amount:.2f}

----------------------------------------
税率: {invoice.tax_rate * 100:.0f}%
税额: ¥{invoice.tax_amount:.2f}
价税合计: ¥{invoice.amount:.2f}

----------------------------------------
销售方信息
----------------------------------------
名称: {invoice.seller_name}
纳税人识别号: {invoice.seller_tax_number}

备注: {invoice.remark or "-"}
========================================
"""
        return content.encode("utf-8")

    def _amount_to_chinese(self, amount: float) -> str:
        """
        金额转中文大写

        Args:
            amount: 金额数值

        Returns:
            中文大写金额
        """
        digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
        units = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]

        # 处理小数部分
        amount_str = f"{amount:.2f}"
        integer_part, decimal_part = amount_str.split(".")

        result = ""

        # 整数部分
        integer_len = len(integer_part)
        for i, char in enumerate(integer_part):
            digit = int(char)
            unit_index = integer_len - i - 1

            if digit != 0:
                result += digits[digit] + units[unit_index]
            else:
                # 处理零的情况
                if unit_index in [4, 8]:  # 万、亿位
                    result += units[unit_index]
                elif result and not result.endswith("零"):
                    result += "零"

        # 去除末尾的零
        result = result.rstrip("零")
        if not result:
            result = "零"

        result += "元"

        # 小数部分
        jiao = int(decimal_part[0])
        fen = int(decimal_part[1])

        if jiao == 0 and fen == 0:
            result += "整"
        else:
            if jiao != 0:
                result += digits[jiao] + "角"
            elif fen != 0:
                result += "零"
            if fen != 0:
                result += digits[fen] + "分"

        return result

    async def issue_invoice(self, invoice_id: int, issued_by: str = "系统") -> Invoice:
        """
        开具发票

        Args:
            invoice_id: 发票ID
            issued_by: 开票人

        Returns:
            更新后的发票对象
        """
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        if invoice.status != InvoiceStatus.PENDING:
            raise ValueError(f"发票状态不正确，无法开具: {invoice.status}")

        # 生成PDF
        if not invoice.pdf_path:
            await self.generate_pdf(invoice_id)

        # 更新状态
        invoice.status = InvoiceStatus.ISSUED
        invoice.issued_at = datetime.utcnow()
        invoice.issued_by = issued_by

        await self.db.commit()
        await self.db.refresh(invoice)

        logger.info(f"发票开具成功: invoice={invoice.invoice_number}, issued_by={issued_by}")

        return invoice

    async def send_invoice(
        self,
        invoice_id: int,
        recipient_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送发票

        Args:
            invoice_id: 发票ID
            recipient_email: 接收邮箱（可选，默认使用发票记录中的邮箱）

        Returns:
            发送结果
        """
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        if invoice.status not in [InvoiceStatus.ISSUED, InvoiceStatus.SENT]:
            raise ValueError(f"发票状态不正确，无法发送: {invoice.status}")

        # 确定收件邮箱
        email = recipient_email or invoice.recipient_email
        if not email:
            raise ValueError("未指定接收邮箱")

        # 确保PDF已生成
        if not invoice.pdf_path:
            await self.generate_pdf(invoice_id)

        # 发送邮件
        try:
            await self._send_invoice_email(invoice, email)

            # 更新发票状态
            invoice.status = InvoiceStatus.SENT
            invoice.sent_at = datetime.utcnow()
            if recipient_email:
                invoice.recipient_email = recipient_email

            await self.db.commit()

            logger.info(f"发票发送成功: invoice={invoice.invoice_number}, email={email}")

            return {
                "success": True,
                "invoice_number": invoice.invoice_number,
                "recipient_email": email,
                "sent_at": invoice.sent_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"发票发送失败: invoice={invoice.invoice_number}, error={e}")
            return {
                "success": False,
                "invoice_number": invoice.invoice_number,
                "error": str(e),
            }

    async def _send_invoice_email(self, invoice: Invoice, recipient_email: str):
        """
        发送发票邮件

        Args:
            invoice: 发票对象
            recipient_email: 收件人邮箱
        """
        # 使用通知服务发送邮件
        try:
            from tasks.notification_tasks import send_email_notification

            # 读取PDF附件
            pdf_content = None
            if invoice.pdf_path and Path(invoice.pdf_path).exists():
                with open(invoice.pdf_path, "rb") as f:
                    pdf_content = f.read()

            # 发送邮件任务
            send_email_notification.delay(
                recipient=recipient_email,
                subject=f"电子发票 - {invoice.invoice_number}",
                content=f"""
                <h2>电子发票</h2>
                <p>尊敬的客户，您好！</p>
                <p>您的电子发票已开具，详情如下：</p>
                <ul>
                    <li>发票号码：{invoice.invoice_number}</li>
                    <li>发票金额：¥{invoice.amount:.2f}</li>
                    <li>开票日期：{invoice.issued_at.strftime("%Y-%m-%d") if invoice.issued_at else "-"}</li>
                </ul>
                <p>请查收附件中的电子发票PDF文件。</p>
                <p>如有疑问，请联系客服。</p>
                """,
                attachment_name=f"{invoice.invoice_number}.pdf" if pdf_content else None,
                attachment_content=pdf_content,
            )
        except ImportError:
            # 如果通知任务模块不可用，记录日志
            logger.warning(f"通知服务不可用，发票 {invoice.invoice_number} 需手动发送到 {recipient_email}")

    async def cancel_invoice(
        self,
        invoice_id: int,
        reason: str,
    ) -> Invoice:
        """
        作废发票

        Args:
            invoice_id: 发票ID
            reason: 作废原因

        Returns:
            更新后的发票对象
        """
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise ValueError(f"发票不存在: {invoice_id}")

        if invoice.status == InvoiceStatus.CANCELLED:
            raise ValueError("发票已作废")

        # 更新状态
        invoice.status = InvoiceStatus.CANCELLED
        invoice.cancelled_at = datetime.utcnow()
        invoice.cancel_reason = reason

        await self.db.commit()
        await self.db.refresh(invoice)

        logger.info(f"发票作废成功: invoice={invoice.invoice_number}, reason={reason}")

        return invoice

    async def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """获取发票详情"""
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """根据发票号码获取发票"""
        stmt = select(Invoice).where(Invoice.invoice_number == invoice_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_invoices(
        self,
        tenant_id: str,
        status: Optional[InvoiceStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Invoice]:
        """
        获取租户发票列表

        Args:
            tenant_id: 租户ID
            status: 筛选状态（可选）
            offset: 偏移量
            limit: 数量限制

        Returns:
            发票列表
        """
        stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(Invoice.status == status)

        stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ===== 发票抬头管理 =====

    async def save_invoice_title(
        self,
        tenant_id: str,
        title_name: str,
        tax_number: Optional[str] = None,
        address: Optional[str] = None,
        bank_account: Optional[str] = None,
        invoice_type: InvoiceType = InvoiceType.ELECTRONIC,
        is_default: bool = False,
    ) -> InvoiceTitle:
        """
        保存发票抬头

        Args:
            tenant_id: 租户ID
            title_name: 抬头名称
            tax_number: 税号
            address: 地址电话
            bank_account: 开户行及账号
            invoice_type: 发票类型
            is_default: 是否默认

        Returns:
            发票抬头对象
        """
        # 如果设置为默认，取消其他默认抬头
        if is_default:
            await self.db.execute(
                update(InvoiceTitle)
                .where(InvoiceTitle.tenant_id == tenant_id)
                .values(is_default=False)
            )

        title = InvoiceTitle(
            tenant_id=tenant_id,
            title_name=title_name,
            tax_number=tax_number,
            address=address,
            bank_account=bank_account,
            invoice_type=invoice_type,
            is_default=is_default,
        )

        self.db.add(title)
        await self.db.commit()
        await self.db.refresh(title)

        logger.info(f"保存发票抬头成功: tenant={tenant_id}, title={title_name}")

        return title

    async def get_invoice_titles(self, tenant_id: str) -> List[InvoiceTitle]:
        """获取租户的发票抬头列表"""
        stmt = select(InvoiceTitle).where(
            InvoiceTitle.tenant_id == tenant_id
        ).order_by(InvoiceTitle.is_default.desc(), InvoiceTitle.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_default_title(self, tenant_id: str) -> Optional[InvoiceTitle]:
        """获取默认发票抬头"""
        stmt = select(InvoiceTitle).where(
            and_(
                InvoiceTitle.tenant_id == tenant_id,
                InvoiceTitle.is_default == True,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_invoice_title(self, title_id: int, tenant_id: str) -> bool:
        """删除发票抬头"""
        stmt = select(InvoiceTitle).where(
            and_(
                InvoiceTitle.id == title_id,
                InvoiceTitle.tenant_id == tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        title = result.scalar_one_or_none()

        if not title:
            return False

        await self.db.delete(title)
        await self.db.commit()

        logger.info(f"删除发票抬头: id={title_id}, tenant={tenant_id}")

        return True

    def _generate_invoice_number(self) -> str:
        """
        生成发票号码

        格式: INV + 年月日 + 6位随机数
        示例: INV202401150123456
        """
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"INV{date_str}{random_str}"
