'use client';

import { Typography } from 'antd';
import { Message } from '@/types';

const { Text } = Typography;

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (isSystem) {
    return (
      <div className="text-center py-2">
        <Text type="secondary" className="text-xs bg-gray-100 px-3 py-1 rounded-full">
          {message.content}
        </Text>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`
          max-w-[70%] px-4 py-3 rounded-lg shadow-sm
          ${
            isUser
              ? 'bg-white border border-gray-200 rounded-bl-none'
              : 'bg-blue-50 border border-blue-200 rounded-br-none'
          }
        `}
      >
        <div
          className="text-sm leading-relaxed whitespace-pre-wrap"
          dangerouslySetInnerHTML={{
            __html: message.content.replace(/\n/g, '<br>'),
          }}
        />
        <div
          className={`text-xs mt-2 ${isUser ? 'text-left' : 'text-right'}`}
        >
          <Text type="secondary">{formatTime(message.created_at)}</Text>
        </div>
      </div>
    </div>
  );
}
