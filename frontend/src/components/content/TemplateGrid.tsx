'use client';

import { Card, Row, Col, Tag, Typography, Empty } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import type { ContentTemplate } from '@/types';

const { Text } = Typography;

interface TemplateCardProps {
  template: ContentTemplate;
  selected: boolean;
  onSelect: (template: ContentTemplate) => void;
}

function TemplateCard({ template, selected, onSelect }: TemplateCardProps) {
  return (
    <Card
      hoverable
      className={`relative cursor-pointer transition-all ${
        selected ? 'ring-2 ring-blue-500' : ''
      }`}
      onClick={() => onSelect(template)}
      cover={
        template.thumbnail_url ? (
          <img
            alt={template.name}
            src={template.thumbnail_url}
            className="h-40 object-cover"
          />
        ) : (
          <div className="h-40 bg-gray-100 flex items-center justify-center">
            <Text type="secondary">暂无预览</Text>
          </div>
        )
      }
    >
      {selected && (
        <div className="absolute top-2 right-2">
          <CheckCircleOutlined className="text-2xl text-blue-500" />
        </div>
      )}
      <Card.Meta
        title={template.name}
        description={
          <div className="space-y-2">
            <div className="flex flex-wrap gap-1">
              {template.platform_presets &&
                Object.keys(template.platform_presets).map((platform) => (
                  <Tag key={platform} color="blue">
                    {platform}
                  </Tag>
                ))}
            </div>
            <Text type="secondary" className="text-xs">
              使用 {template.usage_count} 次
            </Text>
          </div>
        }
      />
    </Card>
  );
}

interface TemplateGridProps {
  templates: ContentTemplate[];
  selectedTemplate: ContentTemplate | null;
  onSelectTemplate: (template: ContentTemplate) => void;
  loading?: boolean;
}

export default function TemplateGrid({
  templates,
  selectedTemplate,
  onSelectTemplate,
  loading = false,
}: TemplateGridProps) {
  if (loading) {
    return (
      <Row gutter={[16, 16]}>
        {[1, 2, 3, 4].map((i) => (
          <Col key={i} xs={24} sm={12} md={8} lg={6}>
            <Card loading />
          </Col>
        ))}
      </Row>
    );
  }

  if (templates.length === 0) {
    return <Empty description="暂无模板" />;
  }

  return (
    <Row gutter={[16, 16]}>
      {templates.map((template) => (
        <Col key={template.id} xs={24} sm={12} md={8} lg={6}>
          <TemplateCard
            template={template}
            selected={selectedTemplate?.id === template.id}
            onSelect={onSelectTemplate}
          />
        </Col>
      ))}
    </Row>
  );
}
