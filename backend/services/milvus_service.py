"""
Milvus 向量数据库服务
"""
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from core.config import settings


def _collection_exists(name: str) -> bool:
    """检查 collection 是否存在（兼容 Zilliz Cloud Serverless）"""
    try:
        return name in utility.list_collections()
    except Exception:
        return False


class MilvusService:
    """Milvus 向量数据库服务（租户级 Collection 隔离）"""

    def __init__(self, tenant_id: str):
        """
        初始化 Milvus 服务

        Args:
            tenant_id: 租户 ID
        """
        self.tenant_id = tenant_id
        self.collection_name = f"kb_{tenant_id.replace('-', '_')}"
        self._connect()

    def _connect(self) -> None:
        """连接到 Milvus"""
        try:
            connections.connect(
                alias="default",
                uri=settings.milvus_uri,
                token=settings.milvus_token,
            )
            # Zilliz Cloud Serverless 的 has_collection 在 collection 不存在时
            # 抛异常而非返回 False，需要 monkey-patch 修复
            self._patch_has_collection()
        except Exception as e:
            print(f"✗ 连接 Milvus 失败: {e}")
            raise

    @staticmethod
    def _patch_has_collection() -> None:
        """修复 Zilliz Cloud Serverless 的 has_collection 兼容性问题"""
        conn = connections._fetch_handler("default")
        if conn is None or getattr(conn, '_has_collection_patched', False):
            return
        original = conn.has_collection

        def safe_has_collection(name, timeout=None, **kwargs):
            try:
                return original(name, timeout=timeout, **kwargs)
            except Exception:
                # has_collection 失败时回退到 list_collections
                try:
                    cols = conn.list_collections()
                    return name in cols
                except Exception:
                    return False

        conn.has_collection = safe_has_collection
        conn._has_collection_patched = True

    def create_collection_if_not_exists(self, dimension: int | None = None) -> Collection:
        """
        创建 Collection（如果不存在）

        Args:
            dimension: 向量维度；为 None 时回退到 settings.embedding_dimension

        Returns:
            Collection 实例
        """
        dim = dimension or settings.embedding_dimension

        if _collection_exists(self.collection_name):
            collection = Collection(self.collection_name)
            collection.load()
            return collection

        # 定义字段
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            ),
            FieldSchema(
                name="tenant_id",
                dtype=DataType.VARCHAR,
                max_length=64,
            ),
            FieldSchema(
                name="knowledge_id",
                dtype=DataType.VARCHAR,
                max_length=64,
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=65535,
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=dim,
            ),
        ]

        # 创建 Schema
        schema = CollectionSchema(
            fields=fields,
            description=f"知识库向量 Collection（租户: {self.tenant_id}）",
        )

        # 创建 Collection
        collection = Collection(
            name=self.collection_name,
            schema=schema,
        )

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="vector", index_params=index_params)

        # 加载到内存
        collection.load()

        print(f"✓ 创建 Collection: {self.collection_name}")
        return collection

    async def insert_vectors(
        self,
        knowledge_items: list[dict[str, Any]],
        vectors: list[list[float]],
        dimension: int | None = None,
    ) -> list[str]:
        """
        插入向量

        Args:
            knowledge_items: 知识库项列表
            vectors: 对应的向量列表
            dimension: 向量维度（用于首次创建 collection）

        Returns:
            插入的 ID 列表
        """
        collection = self.create_collection_if_not_exists(dimension=dimension)

        # 准备数据
        ids = [item["id"] for item in knowledge_items]
        tenant_ids = [self.tenant_id] * len(knowledge_items)
        knowledge_ids = [item["knowledge_id"] for item in knowledge_items]
        contents = [item["content"][:65535] for item in knowledge_items]  # 限制长度

        entities = [
            ids,
            tenant_ids,
            knowledge_ids,
            contents,
            vectors,
        ]

        collection.insert(entities)
        collection.flush()

        print(f"✓ 插入 {len(ids)} 条向量到 Milvus")
        return ids

    async def search_vectors(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        搜索相似向量

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            filter_expr: 过滤表达式

        Returns:
            搜索结果列表
        """
        collection = self.create_collection_if_not_exists()

        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }

        # 搜索
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["knowledge_id", "content", "tenant_id"],
        )

        # 格式化结果
        formatted_results = []
        if results:
            for hits in results:
                for hit in hits:
                    formatted_results.append(
                        {
                            "id": hit.id,
                            "knowledge_id": hit.entity.get("knowledge_id"),
                            "content": hit.entity.get("content"),
                            "score": hit.distance,  # L2 距离（越小越相似）
                            "similarity": 1 / (1 + hit.distance),  # 转换为相似度
                        }
                    )

        return formatted_results

    async def delete_vectors(self, knowledge_ids: list[str]) -> int:
        """
        删除向量

        Args:
            knowledge_ids: 知识库 ID 列表

        Returns:
            删除的数量
        """
        collection = self.create_collection_if_not_exists()

        # 构建删除表达式（collection 已按租户隔离，无需 tenant_id 过滤）
        ids_str = ", ".join([f"'{kid}'" for kid in knowledge_ids])
        expr = f"knowledge_id in [{ids_str}]"

        # 删除
        collection.delete(expr)
        collection.flush()

        print(f"✓ 删除 {len(knowledge_ids)} 条向量")
        return len(knowledge_ids)

    def drop_tenant_collection(self) -> None:
        """删除当前租户的 Collection"""
        if not _collection_exists(self.collection_name):
            return
        utility.drop_collection(self.collection_name)

    def get_collection_stats(self) -> dict[str, Any]:
        """
        获取 Collection 统计信息

        Returns:
            统计信息
        """
        if not _collection_exists(self.collection_name):
            return {
                "exists": False,
                "name": self.collection_name,
            }

        collection = Collection(self.collection_name)

        return {
            "exists": True,
            "name": self.collection_name,
            "num_entities": collection.num_entities,
        }

    @staticmethod
    def disconnect() -> None:
        """断开连接"""
        try:
            connections.disconnect(alias="default")
        except Exception as e:
            print(f"断开 Milvus 连接失败: {e}")
