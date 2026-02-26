'use client';

import { memo } from 'react';
import { Typography } from 'antd';
import { Message } from '@/types';

const { Text } = Typography;

interface MessageBubbleProps {
  message: Message;
}

function renderContent(content: string) {
  return content.split('\n').map((line, i, arr) => (
    <span key={i}>
      {line}
      {i < arr.length - 1 && <br />}
    </span>
  ));
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isStreaming = message.isStreaming === true;

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
        <Text type="secondary" className="text-xs px-3 py-1 rounded-full" style={{ background: '#EDE9FE' }}>
          {message.content}
        </Text>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
      <div
        className="max-w-[70%] px-4 py-3 shadow-sm"
        style={{
          borderRadius: isUser ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
          background: isUser ? '#ffffff' : '#EDE9FE',
          border: isUser ? '1px solid #E5E7EB' : '1px solid #C7D2FE',
        }}
      >
        <div className="text-sm leading-relaxed" style={{ color: '#1E1B4B' }}>
          {renderContent(message.content)}
          {isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-indigo-500 ml-0.5 animate-pulse align-middle" />
          )}
        </div>
        {!isStreaming && (
          <div className={`text-xs mt-2 ${isUser ? 'text-left' : 'text-right'}`}>
            <Text type="secondary" style={{ fontSize: '0.7rem' }}>
              {formatTime(message.created_at)}
            </Text>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(MessageBubble);