'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Select, message, Typography, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { adminManagementApi } from '@/lib/api/admin';
import { AdminInfo, AdminRole, AdminStatus, AdminCreateRequest, AdminUpdateRequest } from '@/types/admin';
import { useAdminStore } from '@/store';

const { Title } = Typography;

const roleOptions = [
  { value: '', label: '全部角色' },
  { value: 'super_admin', label: '超级管理员' },
  { value: 'operation_admin', label: '运营管理员' },
  { value: 'support_admin', label: '客服管理员' },
  { value: 'readonly_admin', label: '只读管理员' },
];

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '正常' },
  { value: 'inactive', label: '未激活' },
  { value: 'suspended', label: '已停用' },
];

const roleConfig: Record<AdminRole, { color: string; label: string }> = {
  super_admin: { color: 'red', label: '超级管理员' },
  operation_admin: { color: 'blue', label: '运营管理员' },
  support_admin: { color: 'green', label: '客服管理员' },
  readonly_admin: { color: 'default', label: '只读管理员' },
};

const statusConfig: Record<AdminStatus, { color: string; label: string }> = {
  active: { color: 'green', label: '正常' },
  inactive: { color: 'orange', label: '未激活' },
  suspended: { color: 'red', label: '已停用' },
};

export default function AdminsPage() {
  const { admin: currentAdmin } = useAdminStore();
  const [loading, setLoading] = useState(true);
  const [admins, setAdmins] = useState<AdminInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [role, setRole] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [keyword, setKeyword] = useState<string>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<AdminInfo | null>(null);
  const [form] = Form.useForm();

  const fetchAdmins = useCallback(async () => {
    setLoading(true);
    try {
      const response = await adminManagementApi.list({
        page,
        size: pageSize,
        role: (role as AdminRole) || undefined,
        status: (status as AdminStatus) || undefined,
        keyword: keyword || undefined,
      });
      if (response.success && response.data) {
        setAdmins(response.data.items);
        setTotal(response.data.total);
      }
    } catch (error) {
      console.error('Failed to fetch admins:', error);
      message.error('加载管理员列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, role, status, keyword]);

  useEffect(() => {
    fetchAdmins();
  }, [fetchAdmins]);

  const handleSearch = () => {
    setPage(1);
    fetchAdmins();
  };

  const handleCreate = () => {
    setEditingAdmin(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (admin: AdminInfo) => {
    setEditingAdmin(admin);
    form.setFieldsValue({
      email: admin.email,
      phone: admin.phone,
      role: admin.role,
      status: admin.status,
    });
    setModalOpen(true);
  };

  const handleDelete = (admin: AdminInfo) => {
    if (admin.admin_id === currentAdmin?.admin_id) {
      message.warning('不能删除自己');
      return;
    }

    Modal.confirm({
      title: '确认删除管理员？',
      content: `将删除管理员 ${admin.username}，此操作不可恢复`,
      onOk: async () => {
        try {
          const response = await adminManagementApi.delete(admin.admin_id);
          if (response.success) {
            message.success('删除成功');
            fetchAdmins();
          } else {
            message.error(response.error?.message || '删除失败');
          }
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingAdmin) {
        // Update existing admin
        const updateData: AdminUpdateRequest = {
          email: values.email,
          phone: values.phone,
          role: values.role,
          status: values.status,
        };
        const response = await adminManagementApi.update(editingAdmin.admin_id, updateData);
        if (response.success) {
          message.success('更新成功');
          setModalOpen(false);
          fetchAdmins();
        } else {
          message.error(response.error?.message || '更新失败');
        }
      } else {
        // Create new admin
        const createData: AdminCreateRequest = {
          username: values.username,
          password: values.password,
          email: values.email,
          phone: values.phone,
          role: values.role,
        };
        const response = await adminManagementApi.create(createData);
        if (response.success) {
          message.success('创建成功');
          setModalOpen(false);
          form.resetFields();
          fetchAdmins();
        } else {
          message.error(response.error?.message || '创建失败');
        }
      }
    } catch (error) {
      console.error('Submit failed:', error);
    }
  };

  const columns: ColumnsType<AdminInfo> = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 200,
      render: (email: string | null) => email || '-',
    },
    {
      title: '电话',
      dataIndex: 'phone',
      key: 'phone',
      width: 140,
      render: (phone: string | null) => phone || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 120,
      render: (r: AdminRole) => {
        const config = roleConfig[r] || { color: 'default', label: r };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: AdminStatus) => {
        const config = statusConfig[s] || { color: 'default', label: s };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      width: 180,
      render: (date: string | null) => date ? new Date(date).toLocaleString('zh-CN') : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          {record.admin_id !== currentAdmin?.admin_id && (
            <Tooltip title="删除">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Title level={4} className="mb-0">管理员管理</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          添加管理员
        </Button>
      </div>

      <Card>
        {/* Filters */}
        <div className="mb-4 flex flex-wrap gap-4">
          <Input
            placeholder="搜索用户名/邮箱"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            value={role}
            onChange={setRole}
            options={roleOptions}
            style={{ width: 140 }}
          />
          <Select
            value={status}
            onChange={setStatus}
            options={statusOptions}
            style={{ width: 140 }}
          />
          <Button type="primary" onClick={handleSearch}>
            搜索
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchAdmins}>
            刷新
          </Button>
        </div>

        {/* Table */}
        <Table
          dataSource={admins}
          columns={columns}
          rowKey="admin_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Create/Edit modal */}
      <Modal
        title={editingAdmin ? '编辑管理员' : '添加管理员'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText={editingAdmin ? '保存' : '创建'}
        cancelText="取消"
        width={480}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ role: 'readonly_admin' }}
        >
          {!editingAdmin && (
            <>
              <Form.Item
                name="username"
                label="用户名"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { min: 3, message: '用户名至少3个字符' },
                ]}
              >
                <Input placeholder="请输入用户名" />
              </Form.Item>
              <Form.Item
                name="password"
                label="密码"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少8个字符' },
                ]}
              >
                <Input.Password placeholder="请输入密码" />
              </Form.Item>
            </>
          )}
          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item
            name="phone"
            label="电话"
          >
            <Input placeholder="请输入电话（选填）" />
          </Form.Item>
          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select
              options={roleOptions.filter(r => r.value !== '')}
              placeholder="请选择角色"
            />
          </Form.Item>
          {editingAdmin && (
            <Form.Item
              name="status"
              label="状态"
            >
              <Select
                options={statusOptions.filter(s => s.value !== '')}
                placeholder="请选择状态"
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
