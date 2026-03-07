"""
数据库初始化脚本
- 创建所有表
- 创建默认超级管理员
- 创建默认套餐配置
- 预置系统模板和平台规范数据
"""
import asyncio
import json
import sys
from sqlalchemy import text

from db.session import engine, AsyncSessionLocal
from models.base import Base
# 导入所有模型确保 Base.metadata 能发现所有表
import models  # noqa: F401
from models.admin import Admin
from core.security import hash_password
from core.permissions import AdminRole


async def seed_content_templates(session):
    """预置系统内容模板"""
    print("📝 预置系统内容模板...")

    # 检查是否已有系统模板
    result = await session.execute(
        text("SELECT COUNT(*) FROM content_templates WHERE is_system = 1")
    )
    count = result.scalar()
    if count and count > 0:
        print("ℹ️  系统模板已存在，跳过创建")
        return

    # ===== 海报模板 =====
    poster_templates = [
        {
            "name": "白底商品主图",
            "category": "poster",
            "scene_type": "main_image",
            "prompt_template": "A professional product photo of {{product_name}}, {{style}} style, pure white background, centered composition, studio lighting, high resolution, commercial photography",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "风格", "source": "user_input", "required": False, "default": "minimalist"}
            ]),
            "style_options": json.dumps(["简约", "高端", "日系", "韩系", "现代"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800"},
                "pdd": {"size": "750x750"},
                "jd": {"size": "800x800"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark,logo,blur"}),
            "sort_order": 1,
        },
        {
            "name": "场景化商品主图",
            "category": "poster",
            "scene_type": "main_image",
            "prompt_template": "{{product_name}} in a {{scene}} setting, {{style}} style, natural lighting, lifestyle photography, high quality",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "scene", "label": "场景", "source": "user_input", "required": False, "default": "modern home"},
                {"key": "style", "label": "风格", "source": "user_input", "required": False, "default": "lifestyle"}
            ]),
            "style_options": json.dumps(["生活化", "温馨", "时尚", "户外", "办公"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800"},
                "pdd": {"size": "750x750"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 2,
        },
        {
            "name": "商品详情长图",
            "category": "poster",
            "scene_type": "detail_image",
            "prompt_template": "Detailed product showcase of {{product_name}}, multiple angles, feature highlights, {{style}} layout, vertical composition",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "布局风格", "source": "user_input", "required": False, "default": "modern"}
            ]),
            "style_options": json.dumps(["现代", "简洁", "信息丰富", "图文并茂"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x1200"},
                "pdd": {"size": "750x1000"}
            }),
            "default_params": json.dumps({"negative_prompt": "blur,low quality"}),
            "sort_order": 3,
        },
        {
            "name": "促销活动海报",
            "category": "poster",
            "scene_type": "promo_poster",
            "prompt_template": "Promotional poster for {{product_name}}, {{discount}} discount, {{theme}} theme, eye-catching design, bold colors",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "discount", "label": "折扣信息", "source": "user_input", "required": False, "default": "special offer"},
                {"key": "theme", "label": "主题", "source": "user_input", "required": False, "default": "sale"}
            ]),
            "style_options": json.dumps(["618大促", "双11", "新品上市", "限时特惠", "清仓"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800"},
                "douyin": {"size": "1080x1920"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 4,
        },
        {
            "name": "节日主题海报",
            "category": "poster",
            "scene_type": "promo_poster",
            "prompt_template": "{{festival}} themed poster featuring {{product_name}}, festive atmosphere, {{style}} design, celebratory mood",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "festival", "label": "节日", "source": "user_input", "required": False, "default": "holiday"},
                {"key": "style", "label": "风格", "source": "user_input", "required": False, "default": "festive"}
            ]),
            "style_options": json.dumps(["春节", "情人节", "中秋", "圣诞", "国庆"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 5,
        },
        {
            "name": "直播封面",
            "category": "poster",
            "scene_type": "promo_poster",
            "prompt_template": "Live streaming cover for {{product_name}}, attention-grabbing, {{style}} design, broadcast theme",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "风格", "source": "user_input", "required": False, "default": "dynamic"}
            ]),
            "style_options": json.dumps(["动感", "热闹", "专业", "亲和"]),
            "platform_presets": json.dumps({
                "douyin": {"size": "1080x1920"},
                "kuaishou": {"size": "1080x1920"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 6,
        },
        {
            "name": "店铺Banner",
            "category": "poster",
            "scene_type": "promo_poster",
            "prompt_template": "Store banner featuring {{product_name}}, {{theme}} theme, wide format, professional design",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "theme", "label": "主题", "source": "user_input", "required": False, "default": "brand"}
            ]),
            "style_options": json.dumps(["品牌", "促销", "新品", "推荐"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "1920x600"},
                "jd": {"size": "1920x600"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 7,
        },
        {
            "name": "商品对比图",
            "category": "poster",
            "scene_type": "detail_image",
            "prompt_template": "Product comparison image of {{product_name}}, before and after, side by side layout, clear differences",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True}
            ]),
            "style_options": json.dumps(["对比", "升级", "优势"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 8,
        },
    ]

    # ===== 视频模板 =====
    video_templates = [
        {
            "name": "商品主图视频",
            "category": "video",
            "scene_type": "main_video",
            "prompt_template": "Product showcase video of {{product_name}}, 360-degree rotation, {{style}} presentation, clean background, smooth camera movement",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "风格", "source": "user_input", "required": False, "default": "professional"}
            ]),
            "style_options": json.dumps(["专业", "简约", "动感", "高端"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800", "duration": "9-30"},
                "pdd": {"size": "750x750", "duration": "9-30"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark,blur"}),
            "sort_order": 1,
        },
        {
            "name": "商品展示短视频",
            "category": "video",
            "scene_type": "short_video",
            "prompt_template": "Short video showcasing {{product_name}}, {{scene}} background, dynamic presentation, engaging visuals",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "scene", "label": "场景", "source": "user_input", "required": False, "default": "lifestyle"}
            ]),
            "style_options": json.dumps(["生活化", "时尚", "创意", "趣味"]),
            "platform_presets": json.dumps({
                "douyin": {"size": "1080x1920", "duration": "15-60"},
                "kuaishou": {"size": "1080x1920", "duration": "15-60"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 2,
        },
        {
            "name": "商品详情视频",
            "category": "video",
            "scene_type": "detail_video",
            "prompt_template": "Detailed product video of {{product_name}}, feature demonstration, close-up shots, {{style}} narration style",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "讲解风格", "source": "user_input", "required": False, "default": "informative"}
            ]),
            "style_options": json.dumps(["详细讲解", "快速介绍", "专业评测"]),
            "platform_presets": json.dumps({
                "taobao": {"size": "800x800", "duration": "30-60"}
            }),
            "default_params": json.dumps({"negative_prompt": "blur,low quality"}),
            "sort_order": 3,
        },
        {
            "name": "开箱视频",
            "category": "video",
            "scene_type": "detail_video",
            "prompt_template": "Unboxing video of {{product_name}}, first impression, packaging reveal, {{style}} presentation",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "风格", "source": "user_input", "required": False, "default": "exciting"}
            ]),
            "style_options": json.dumps(["兴奋", "专业", "详细", "快速"]),
            "platform_presets": json.dumps({
                "douyin": {"size": "1080x1920", "duration": "30-60"}
            }),
            "default_params": json.dumps({"negative_prompt": "text,watermark"}),
            "sort_order": 4,
        },
        {
            "name": "使用教程视频",
            "category": "video",
            "scene_type": "detail_video",
            "prompt_template": "Tutorial video for {{product_name}}, step-by-step guide, {{style}} instruction style, clear demonstration",
            "variables": json.dumps([
                {"key": "product_name", "label": "商品名称", "source": "product.title", "required": True},
                {"key": "style", "label": "教学风格", "source": "user_input", "required": False, "default": "clear"}
            ]),
            "style_options": json.dumps(["清晰", "详细", "快速", "专业"]),
            "platform_presets": json.dumps({
                "douyin": {"size": "1080x1920", "duration": "30-90"}
            }),
            "default_params": json.dumps({"negative_prompt": "blur,confusing"}),
            "sort_order": 5,
        },
    ]

    insert_sql = text("""
        INSERT INTO content_templates
        (tenant_id, name, category, scene_type, prompt_template, variables,
         style_options, platform_presets, default_params, is_system, is_active, sort_order, usage_count)
        VALUES (NULL, :name, :category, :scene_type, :prompt_template, :variables,
                :style_options, :platform_presets, :default_params, 1, 1, :sort_order, 0)
    """)

    for tmpl in poster_templates + video_templates:
        await session.execute(insert_sql, tmpl)

    await session.commit()
    print(f"✅ 系统模板创建完成（海报 {len(poster_templates)} 个 + 视频 {len(video_templates)} 个）")


async def seed_platform_media_specs(session):
    """预置平台媒体规范"""
    print("📐 预置平台媒体规范...")

    result = await session.execute(
        text("SELECT COUNT(*) FROM platform_media_specs")
    )
    count = result.scalar()
    if count and count > 0:
        print("ℹ️  平台规范已存在，跳过创建")
        return

    platform_specs = [
        # 淘宝
        {"platform_type": "taobao", "media_type": "main_image", "spec_name": "淘宝商品主图",
         "width": 800, "height": 800, "max_file_size": 3145728, "format": "jpg,png", "duration_range": None},
        {"platform_type": "taobao", "media_type": "detail_image", "spec_name": "淘宝详情图",
         "width": 800, "height": 1200, "max_file_size": 3145728, "format": "jpg,png", "duration_range": None},
        {"platform_type": "taobao", "media_type": "main_video", "spec_name": "淘宝主图视频",
         "width": 800, "height": 800, "max_file_size": 52428800, "format": "mp4",
         "duration_range": json.dumps({"min": 9, "max": 30})},
        {"platform_type": "taobao", "media_type": "short_video", "spec_name": "淘宝短视频",
         "width": 1080, "height": 1920, "max_file_size": 104857600, "format": "mp4",
         "duration_range": json.dumps({"min": 15, "max": 60})},
        # 拼多多
        {"platform_type": "pdd", "media_type": "main_image", "spec_name": "拼多多商品主图",
         "width": 750, "height": 750, "max_file_size": 2097152, "format": "jpg,png", "duration_range": None},
        {"platform_type": "pdd", "media_type": "detail_image", "spec_name": "拼多多详情图",
         "width": 750, "height": 1000, "max_file_size": 2097152, "format": "jpg,png", "duration_range": None},
        {"platform_type": "pdd", "media_type": "main_video", "spec_name": "拼多多主图视频",
         "width": 750, "height": 750, "max_file_size": 52428800, "format": "mp4",
         "duration_range": json.dumps({"min": 9, "max": 30})},
        {"platform_type": "pdd", "media_type": "short_video", "spec_name": "拼多多短视频",
         "width": 1080, "height": 1920, "max_file_size": 104857600, "format": "mp4",
         "duration_range": json.dumps({"min": 15, "max": 60})},
        # 抖音
        {"platform_type": "douyin", "media_type": "main_image", "spec_name": "抖音商品主图",
         "width": 1080, "height": 1080, "max_file_size": 5242880, "format": "jpg,png", "duration_range": None},
        {"platform_type": "douyin", "media_type": "detail_image", "spec_name": "抖音详情图",
         "width": 1080, "height": 1920, "max_file_size": 5242880, "format": "jpg,png", "duration_range": None},
        {"platform_type": "douyin", "media_type": "main_video", "spec_name": "抖音主图视频",
         "width": 1080, "height": 1920, "max_file_size": 104857600, "format": "mp4",
         "duration_range": json.dumps({"min": 9, "max": 60})},
        {"platform_type": "douyin", "media_type": "short_video", "spec_name": "抖音短视频",
         "width": 1080, "height": 1920, "max_file_size": 209715200, "format": "mp4",
         "duration_range": json.dumps({"min": 15, "max": 180})},
        # 京东
        {"platform_type": "jd", "media_type": "main_image", "spec_name": "京东商品主图",
         "width": 800, "height": 800, "max_file_size": 3145728, "format": "jpg,png", "duration_range": None},
        {"platform_type": "jd", "media_type": "detail_image", "spec_name": "京东详情图",
         "width": 800, "height": 1200, "max_file_size": 3145728, "format": "jpg,png", "duration_range": None},
        {"platform_type": "jd", "media_type": "main_video", "spec_name": "京东主图视频",
         "width": 800, "height": 800, "max_file_size": 52428800, "format": "mp4",
         "duration_range": json.dumps({"min": 9, "max": 30})},
        {"platform_type": "jd", "media_type": "short_video", "spec_name": "京东短视频",
         "width": 1080, "height": 1920, "max_file_size": 104857600, "format": "mp4",
         "duration_range": json.dumps({"min": 15, "max": 60})},
        # 快手
        {"platform_type": "kuaishou", "media_type": "main_image", "spec_name": "快手商品主图",
         "width": 1080, "height": 1080, "max_file_size": 5242880, "format": "jpg,png", "duration_range": None},
        {"platform_type": "kuaishou", "media_type": "detail_image", "spec_name": "快手详情图",
         "width": 1080, "height": 1920, "max_file_size": 5242880, "format": "jpg,png", "duration_range": None},
        {"platform_type": "kuaishou", "media_type": "main_video", "spec_name": "快手主图视频",
         "width": 1080, "height": 1920, "max_file_size": 104857600, "format": "mp4",
         "duration_range": json.dumps({"min": 9, "max": 60})},
        {"platform_type": "kuaishou", "media_type": "short_video", "spec_name": "快手短视频",
         "width": 1080, "height": 1920, "max_file_size": 209715200, "format": "mp4",
         "duration_range": json.dumps({"min": 15, "max": 180})},
    ]

    insert_sql = text("""
        INSERT INTO platform_media_specs
        (platform_type, media_type, spec_name, width, height, max_file_size, format, duration_range)
        VALUES (:platform_type, :media_type, :spec_name, :width, :height,
                :max_file_size, :format, :duration_range)
    """)

    for spec in platform_specs:
        await session.execute(insert_sql, spec)

    await session.commit()
    print(f"✅ 平台规范创建完成（{len(platform_specs)} 条）")


async def init_database():
    """初始化数据库"""
    print("🚀 开始初始化数据库...")

    # 1. 创建所有表
    print("📦 创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建完成")

    # 2. 创建默认超级管理员
    print("👤 创建默认超级管理员...")
    async with AsyncSessionLocal() as session:
        # 检查是否已存在管理员
        result = await session.execute(
            text("SELECT COUNT(*) FROM platform_admins")
        )
        count = result.scalar()

        if count == 0:
            # 创建超级管理员
            super_admin = Admin(
                admin_id="admin_001",
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("admin123456"),
                role=AdminRole.SUPER_ADMIN,
                status="active"
            )
            session.add(super_admin)
            await session.commit()
            print("✅ 默认超级管理员创建成功")
            print("   用户名: admin")
            print("   密码: admin123456")
            print("   ⚠️  请在生产环境中立即修改默认密码！")
        else:
            print("ℹ️  管理员已存在，跳过创建")

    # 3. 预置系统内容模板
    async with AsyncSessionLocal() as session:
        await seed_content_templates(session)

    # 4. 预置平台媒体规范
    async with AsyncSessionLocal() as session:
        await seed_platform_media_specs(session)

    print("🎉 数据库初始化完成！")


async def check_database_connection():
    """检查数据库连接"""
    print("🔍 检查数据库连接...")
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"⏳ 等待数据库启动... ({i + 1}/{max_retries})")
                await asyncio.sleep(retry_interval)
            else:
                print(f"❌ 数据库连接失败: {e}")
                return False
    return False


async def main():
    """主函数"""
    try:
        # 检查数据库连接
        if not await check_database_connection():
            sys.exit(1)
        
        # 初始化数据库
        await init_database()
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
